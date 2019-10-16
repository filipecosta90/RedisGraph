/*
* Copyright 2018-2019 Redis Labs Ltd. and Contributors
*
* This file is available under the Redis Labs Source Available License Agreement
*/

#pragma once

#include "../value.h"
#include "path.h"
#include <stdlib.h>

/**
 * @brief  Creates a new SIPath out of path struct.
 * @param  p: Path struct.
 * @retval SIValue which represents the given struct.
 */
SIValue SIPath_New(Path p);

/**
 * @brief  Clones a given SIPath.
 * @param  p: SIPath.
 * @retval New SIPath with newly allocated path clone.
 */
SIValue SIPath_Clone(SIValue p);

/**
 * @brief  Returns a SIArray with the path edges as SIEdges.
 * @param  p: SIPath
 * @retval SIArray with the path edges.
 */
SIValue SIPath_Relationships(SIValue p);

/**
 * @brief  Retruns a SIEdge in a given position in the relationships array.
 * @note   Assertion will be raised for out of bound indices.
 * @param  p: SIPath.
 * @param  i: Requested index.
 * @retval SIEdge in the requested index.
 */
SIValue SIPath_GetRelationship(SIValue p, size_t i);

/**
 * @brief  Returns SIArray with the nodes in the path as SINodes.
 * @param  p: SIPath.
 * @retval SIArray with the path nodes.
 */
SIValue SIPath_Nodes(SIValue p);

/**
 * @brief  Returns a SINode in a given position in the nodes array.
 * @note   Assertion will be raised for out of bound indeices.
 * @param  p: SIPath.
 * @param  i: Requested index.
 * @retval SINode in the requested index.
 */
SIValue SIPath_GetNode(SIValue p, size_t i);

/**
 * @brief  Returns the path length.
 * @note   The return value is the amount of edges in the path.
 * @param  p: SIPath
 * @retval Path length.
 */
size_t SIPath_Length(SIValue p);

/**
 * @brief  Returns the path size.
 * @note   The return value is the amount of nodes in the path.
 * @param  p: SIPath
 * @retval Path size.
 */
size_t SIPath_Size(SIValue p);

/**
 * @brief  Returns 64 bit hash code of the path.
 * @param  p: SIPath.
 * @retval 64 bit hash code.
 */
XXH64_hash_t SIPath_HashCode(SIValue p);

/**
 * @brief  Prints a SIPath into a given buffer.
 * @param  p: SIPath.
 * @param  buf: print buffer (pointer to pointer to allow re allocation).
 * @param  len: print buffer length.
 * @param  bytesWritten: the actual number of bytes written to the buffer.
 */
void SIPath_ToString(SIValue p, char **buf, size_t *bufferLen, size_t *bytesWritten);

/**
 * @brief  Free SIPath.
 * @param  p: SIPath.
 */
void SIPath_Free(SIValue p);