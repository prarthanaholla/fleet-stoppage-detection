from math import radians, cos, sin, asin, sqrt


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate real-world distance in meters between two GPS coordinates."""
    R = 6371000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c


def compute_speeds(points: list) -> list:
    """
    Compute speed between consecutive GPS points.
    points: list of dicts with keys: lat, lon, location_time_ms
    Returns: list of speeds in m/s (first point speed = 0)
    """
    speeds = [0.0]
    for i in range(1, len(points)):
        lat1, lon1 = points[i-1]['lat'], points[i-1]['lon']
        lat2, lon2 = points[i]['lat'], points[i]['lon']
        t1 = points[i-1]['location_time_ms']
        t2 = points[i]['location_time_ms']
        time_diff = (t2 - t1) / 1000  # convert ms to seconds
        dist = haversine(lat1, lon1, lat2, lon2)
        speed = dist / time_diff if time_diff > 0 else 0.0
        speeds.append(speed)
    return speeds


def edp_recursive(
    points: list,
    start_idx: int,
    end_idx: int,
    threshold: float,
    keep_set: set
) -> None:
    """Recursive Douglas-Peucker geometric simplification."""
    max_dist = 0
    index = -1
    for i in range(start_idx + 1, end_idx):
        x0 = points[i]['lon']
        y0 = points[i]['lat']
        x1 = points[start_idx]['lon']
        y1 = points[start_idx]['lat']
        x2 = points[end_idx]['lon']
        y2 = points[end_idx]['lat']
        num = abs((y2 - y1)*x0 - (x2 - x1)*y0 + x2*y1 - y2*x1)
        den = sqrt((y2 - y1)**2 + (x2 - x1)**2)
        dist = num / den if den != 0 else 0
        if dist > max_dist:
            max_dist = dist
            index = i
    if max_dist > threshold and index != -1:
        keep_set.add(index)
        edp_recursive(points, start_idx, index, threshold, keep_set)
        edp_recursive(points, index, end_idx, threshold, keep_set)


def simplify_with_estc(
    points: list,
    dp_threshold: float = 10.0,
    speed_change_thresh: float = 2.0,
    time_gap_thresh: float = 90.0
) -> list:
    """
    Enhanced Douglas-Peucker with Speed, Time, and Curvature constraints.
    
    points: list of dicts with keys: lat, lon, location_time_ms
    Returns: filtered list of significant points (subset of input)
    
    Keeps points that are:
    - Local speed extrema (acceleration/deceleration events)
    - Sudden speed changes (stops, starts)
    - Time gap points (potential stopovers)
    - Geometrically significant (standard Douglas-Peucker)
    """
    if len(points) < 3:
        return points

    speeds = compute_speeds(points)
    keep_indices = set([0, len(points) - 1])

    for i in range(1, len(points) - 1):
        prev_speed = speeds[i-1]
        curr_speed = speeds[i]
        next_speed = speeds[i+1]

        # Local speed extrema — peaks and valleys
        is_local_max = curr_speed > prev_speed and curr_speed > next_speed
        is_local_min = curr_speed < prev_speed and curr_speed < next_speed
        if is_local_max or is_local_min:
            keep_indices.add(i)

        # Sudden speed change
        if abs(curr_speed - prev_speed) > speed_change_thresh or \
           abs(next_speed - curr_speed) > speed_change_thresh:
            keep_indices.add(i)

    # Time gap constraint — stay points
    for i in range(1, len(points) - 1):
        t_gap1 = (points[i]['location_time_ms'] - points[i-1]['location_time_ms']) / 1000
        t_gap2 = (points[i+1]['location_time_ms'] - points[i]['location_time_ms']) / 1000
        if t_gap1 > time_gap_thresh or t_gap2 > time_gap_thresh:
            keep_indices.add(i)

    # Geometric Douglas-Peucker
    edp_recursive(points, 0, len(points) - 1, dp_threshold, keep_indices)

    # Return significant points in order
    sorted_indices = sorted(keep_indices)
    return [points[i] for i in sorted_indices]