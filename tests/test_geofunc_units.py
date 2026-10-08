def test_suggest_utm_zone():
    from plugin.geofunc.crs_utils_safe import suggest_utm_zone
    z = suggest_utm_zone(-17, 14)
    assert z.startswith('EPSG:32')
