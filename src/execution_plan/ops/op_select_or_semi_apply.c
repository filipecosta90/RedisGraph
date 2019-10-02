/*
 * Copyright 2018-2019 Redis Labs Ltd. and Contributors
 *
 * This file is available under the Redis Labs Source Available License Agreement
 */

#include "op_select_or_semi_apply.h"
#include "../execution_plan.h"

OpBase *NewSelectOrSemiApplyOp(FT_FilterNode *filter) {
	SelectOrSemiApply *selectOrSemiApply = malloc(sizeof(SelectOrSemiApply));
	selectOrSemiApply->r = NULL;
	selectOrSemiApply->op_arg = NULL;
	selectOrSemiApply->filter = filter;

	// Set our Op operations
	OpBase_Init(&selectOrSemiApply->op);
	selectOrSemiApply->op.name = "Select Or Semi Apply";
	selectOrSemiApply->op.type = OPType_SELECT_OR_SEMI_APPLY;
	selectOrSemiApply->op.init = SelectOrSemiApplyInit;
	selectOrSemiApply->op.consume = SelectOrSemiApplyConsume;
	selectOrSemiApply->op.reset = SelectOrSemiApplyReset;
	selectOrSemiApply->op.free = SelectOrSemiApplyFree;

	return(OpBase *) selectOrSemiApply;
}

OpResult SelectOrSemiApplyInit(OpBase *opBase) {
	assert(opBase->childCount == 2);

	SelectOrSemiApply *op = (SelectOrSemiApply *)opBase;
	// Locate right-hand side Argument op tap.
	OpBase *right_handside = op->op.children[1];
	op->op_arg = (Argument *)ExecutionPlan_LocateOp(right_handside, OPType_ARGUMENT);
	if(op->op_arg) assert(op->op_arg->op.childCount == 0);
	return OP_OK;
}

static inline Record _pullFromStream(OpBase *branch) {
	return OpBase_Consume(branch);
}

static Record _pullFromRightStream(SelectOrSemiApply *op) {
	OpBase *right_handside = op->op.children[1];
	OpBase_PropagateReset(right_handside);
	// Propegate record to the top of the right-hand side stream.
	if(op->op_arg) ArgumentSetRecord(op->op_arg, Record_Clone(op->r));
	return _pullFromStream(right_handside);
}

static Record _pullFromLeftStream(SelectOrSemiApply *op) {
	OpBase *left_handside = op->op.children[0];
	return _pullFromStream(left_handside);
}

Record SelectOrSemiApplyConsume(OpBase *opBase) {
	SelectOrSemiApply *op = (SelectOrSemiApply *)opBase;

	while(true) {
		// Try to get a record from left stream.
		op->r = _pullFromLeftStream(op);
		if(!op->r) return NULL; // Depleted.

		// See if record passes filter.
		if(op->filter && FilterTree_applyFilters(op->filter, op->r) != FILTER_PASS) {
			// Record did not pass filter, try to get a new record.
			Record_Free(op->r);
			op->r = NULL;
			continue;
		}

		// Try to get a record from right stream.
		Record righthand_record = _pullFromRightStream(op);
		if(righthand_record) {
			// Don't care for righthand record.
			Record_Free(righthand_record);
			Record r = op->r;
			op->r = NULL;   // Null to avoid double free.
			return r;
		}
		// Did not managed to get a record from right-hand side, loop back and restart.
		Record_Free(op->r);
		op->r = NULL;
	}
}

OpResult SelectOrSemiApplyReset(OpBase *opBase) {
	SelectOrSemiApply *op = (SelectOrSemiApply *)opBase;
	if(op->r) {
		Record_Free(op->r);
		op->r = NULL;
	}
	return OP_OK;
}

void SelectOrSemiApplyFree(OpBase *opBase) {
	SelectOrSemiApply *op = (SelectOrSemiApply *)opBase;

	if(op->r) {
		Record_Free(op->r);
		op->r = NULL;
	}
	if(op->filter) {
		FilterTree_Free(op->filter);
		op->filter = NULL;
	}
}
