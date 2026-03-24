import math

def calculate_distance(lat1, lon1, lat2, lon2):
    if not lat1 or not lon1 or not lat2 or not lon2:
        return 9999.0
    R = 6371.0  # Earth radius in km
    dLat = math.radians(float(lat2) - float(lat1))
    dLon = math.radians(float(lon2) - float(lon1))
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(float(lat1))) \
        * math.cos(math.radians(float(lat2))) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def find_best_donors(cursor, blood_group, req_lat, req_lon, limit=5, requested_district=None):
    # exact match
    cursor.execute("""
        SELECT id, name, email, latitude, longitude, reliability_score, city 
        FROM donors 
        WHERE blood_group = %s AND availability_status = 'Available'
        AND (cooldown_until IS NULL OR cooldown_until <= NOW())
    """, (blood_group,))
    # use dictionary-like fetching if not already configured.
    # since we have raw cursor or dict cursor:
    columns = [col[0] for col in cursor.description]
    donors = [dict(zip(columns, row)) if isinstance(row, tuple) else row for row in cursor.fetchall()]

    scored_donors = []
    for d in donors:
        dist = calculate_distance(req_lat, req_lon, d['latitude'], d['longitude'])
        # Score = Reliability - Distance penalty (1 point per km)
        base_reliability = float(d['reliability_score']) if d['reliability_score'] is not None else 100.0
        dist_penalty = dist if dist < 9999 else 50.0
        
        # District Bonus: +1000 score if in the same district/city
        district_bonus = 0
        if requested_district and d.get('city'):
            req_dist_str = str(requested_district).lower().strip()
            donor_city_str = str(d['city']).lower().strip()
            if req_dist_str in donor_city_str or donor_city_str in req_dist_str:
                district_bonus = 1000.0
                
        score = base_reliability - dist_penalty + district_bonus
        
        scored_donors.append({
            'donor': d,
            'distance': dist,
            'score': score
        })
        
    scored_donors.sort(key=lambda x: x['score'], reverse=True)
    if limit is None:
        return [item['donor'] for item in scored_donors]
    return [item['donor'] for item in scored_donors[:limit]]
