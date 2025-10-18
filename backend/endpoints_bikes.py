# Novo endpoint para bikes paginadas
# Este arquivo contém os novos endpoints que serão adicionados ao server.py

# @api_router.get("/bikes/paginated")
# async def get_bikes_paginated(
#     page: int = Query(1, ge=1),
#     limit: int = Query(20, ge=1, le=100),
#     sort_by: str = Query("newest", regex="^(newest|oldest|alerts|device)$"),
#     category: Optional[str] = Query(None),
#     search: Optional[str] = Query(None),
#     current_user: dict = Depends(get_current_user)
# ):
#     """Get paginated bikes with alert counts"""
#     async with db_pool.acquire() as conn:
#         # Build WHERE clause
#         where_conditions = ["user_id = $1"]
#         params = [current_user['id']]
#         param_count = 2
#         
#         if category and category != "All":
#             where_conditions.append(f"alert_type = ${param_count}")
#             params.append(category)
#             param_count += 1
#         
#         if search:
#             where_conditions.append(f"(tracker_name ILIKE ${param_count} OR device_serial ILIKE ${param_count})")
#             params.append(f"%{search}%")
#             param_count += 1
#         
#         where_clause = " AND ".join(where_conditions)
#         
#         # Get total count of bikes
#         total_query = f"""
#             SELECT COUNT(DISTINCT tracker_name)
#             FROM tracker_alerts
#             WHERE {where_clause}
#         """
#         total_bikes = await conn.fetchval(total_query, *params)
#         
#         # Get bikes with sorting
#         sort_clause = {
#             "newest": "MAX(created_at) DESC",
#             "oldest": "MAX(created_at) ASC",
#             "alerts": "COUNT(*) DESC",
#             "device": "tracker_name ASC"
#         }.get(sort_by, "MAX(created_at) DESC")
#         
#         offset = (page - 1) * limit
#         
#         bikes_query = f"""
#             SELECT 
#                 tracker_name,
#                 device_serial,
#                 COUNT(*) as alert_count,
#                 MAX(created_at) as latest_alert_at,
#                 STRING_AGG(DISTINCT alert_type, ', ') as alert_types
#             FROM tracker_alerts
#             WHERE {where_clause}
#             GROUP BY tracker_name, device_serial
#             ORDER BY {sort_clause}
#             LIMIT ${param_count} OFFSET ${param_count + 1}
#         """
#         
#         params.extend([limit, offset])
#         bikes = await conn.fetch(bikes_query, *params)
#         
#         bikes_list = []
#         for bike in bikes:
#             bikes_list.append({
#                 "tracker_name": bike['tracker_name'],
#                 "device_serial": bike['device_serial'],
#                 "alert_count": bike['alert_count'],
#                 "latest_alert_at": bike['latest_alert_at'].isoformat() if bike['latest_alert_at'] else None,
#                 "alert_types": bike['alert_types']
#             })
#         
#         total_pages = (total_bikes + limit - 1) // limit
#         
#         return {
#             "bikes": bikes_list,
#             "pagination": {
#                 "page": page,
#                 "limit": limit,
#                 "total": total_bikes,
#                 "total_pages": total_pages,
#                 "has_next": page < total_pages,
#                 "has_prev": page > 1
#             }
#         }


# @api_router.get("/bikes/{tracker_name}/history")
# async def get_bike_history(
#     tracker_name: str,
#     page: int = Query(1, ge=1),
#     limit: int = Query(50, ge=1, le=200),
#     current_user: dict = Depends(get_current_user)
# ):
#     """Get alert history for a specific bike"""
#     async with db_pool.acquire() as conn:
#         # Get total alerts for this bike
#         total = await conn.fetchval(
#             "SELECT COUNT(*) FROM tracker_alerts WHERE user_id = $1 AND tracker_name = $2",
#             current_user['id'], tracker_name
#         )
#         
#         offset = (page - 1) * limit
#         
#         # Get alerts
#         alerts = await conn.fetch(
#             """
#             SELECT 
#                 id, alert_type, alert_time, location, latitude, longitude,
#                 device_serial, status, acknowledged, notes, created_at
#             FROM tracker_alerts
#             WHERE user_id = $1 AND tracker_name = $2
#             ORDER BY created_at DESC
#             LIMIT $3 OFFSET $4
#             """,
#             current_user['id'], tracker_name, limit, offset
#         )
#         
#         alert_list = [dict(a) for a in alerts]
#         total_pages = (total + limit - 1) // limit
#         
#         return {
#             "tracker_name": tracker_name,
#             "alerts": alert_list,
#             "pagination": {
#                 "page": page,
#                 "limit": limit,
#                 "total": total,
#                 "total_pages": total_pages,
#                 "has_next": page < total_pages,
#                 "has_prev": page > 1
#             }
#         }
