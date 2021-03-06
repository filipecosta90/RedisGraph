/*
* Copyright 2018-2019 Redis Labs Ltd. and Contributors
*
* This file is available under the Redis Labs Source Available License Agreement
*/

#include "op_distinct.h"
#include "xxhash.h"
#include "../../util/arr.h"

/* Forward declarations. */
static Record DistinctConsume(OpBase *opBase);
static void DistinctFree(OpBase *opBase);

OpBase *NewDistinctOp(const ExecutionPlan *plan) {
	OpDistinct *op = malloc(sizeof(OpDistinct));
	op->found = raxNew();

	OpBase_Init((OpBase *)op, OPType_DISTINCT, "Distinct", NULL, DistinctConsume,
				NULL, NULL, DistinctFree, plan);

	return (OpBase *)op;
}

static Record DistinctConsume(OpBase *opBase) {
	OpDistinct *self = (OpDistinct *)opBase;
	OpBase *child = self->op.children[0];

	while(true) {
		Record r = OpBase_Consume(child);
		if(!r) return NULL;

		unsigned long long const hash = Record_Hash64(r);
		int is_new = raxInsert(self->found, (unsigned char *) &hash, sizeof(hash), NULL, NULL);
		if(is_new) return r;
		Record_Free(r);
	}
}

static void DistinctFree(OpBase *ctx) {
	OpDistinct *op = (OpDistinct *)ctx;
	if(op->found) {
		raxFree(op->found);
		op->found = NULL;
	}
}

