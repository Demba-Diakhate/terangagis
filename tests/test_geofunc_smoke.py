def test_registry_and_base_imports():
    from plugin.geofunc import tool_base, registry, crs_utils
    assert tool_base.GeoTool.name == 'geo_tool'
