def test_registry_and_base_imports():
    from plugin.geofunc import tool_base, registry
    assert tool_base.GeoTool.name == 'geo_tool'
