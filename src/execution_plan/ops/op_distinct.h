/*
* Copyright 2018-2019 Redis Labs Ltd. and Contributors
*
* This file is available under the Redis Labs Source Available License Agreement
*/

#pragma once

#include "op.h"
#include "rax.h"
#include "../execution_plan.h"

typedef struct {
	OpBase op;
	rax *found;
} OpDistinct;

OpBase *NewDistinctOp(const ExecutionPlan *plan);
