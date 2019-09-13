SELECT
  atmosphere_user.username,
  atmosphere_user.date_joined,
  user_allocation_snapshot.compute_used,
  user_allocation_snapshot.burn_rate,
  user_allocation_snapshot.updated
FROM public.user_allocation_snapshot
  LEFT JOIN public.allocation_source ON user_allocation_snapshot.allocation_source_id = allocation_source.id
  LEFT JOIN public.atmosphere_user ON user_allocation_snapshot.user_id = atmosphere_user.id
WHERE
  allocation_source.name = 'TG-ASC160018'
  AND atmosphere_user.is_active
  AND user_allocation_snapshot.updated > '2017-12-01'
  AND user_allocation_snapshot.compute_used > 2000
ORDER BY compute_used DESC;
