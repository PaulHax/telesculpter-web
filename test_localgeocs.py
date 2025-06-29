#!/usr/bin/env python3

from kwiver.vital.types import SFMConstraints
import kwiver.vital.types as vt

# Check for Vector3d variants
print("Looking for Vector3d:")
vector_attrs = [attr for attr in dir(vt) if 'vector' in attr.lower() or 'Vector' in attr]
print(f"Vector-related attributes: {vector_attrs}")

# Check for CRS/SRID options
print("\nLooking for CRS/SRID:")
crs_attrs = [attr for attr in dir(vt) if 'srid' in attr.lower() or 'crs' in attr.lower()]
print(f"CRS-related attributes: {crs_attrs}")

# Check geodesy module
print("\nChecking geodesy:")
geodesy = vt.geodesy
print(f"geodesy type: {type(geodesy)}")
for attr in sorted(dir(geodesy)):
    if not attr.startswith('_'):
        print(f"  {attr}")

# Test GeoPoint creation
print("\nTesting GeoPoint creation:")
try:
    # Try with WGS84 SRID
    import numpy as np
    coords = np.array([-77.341739, 38.198016, 1054.40002441])
    
    # Check if there's a WGS84 constant
    if hasattr(geodesy, 'SRID'):
        srid = geodesy.SRID
        print(f"SRID type: {type(srid)}")
        for attr in sorted(dir(srid)):
            if not attr.startswith('_'):
                print(f"  SRID.{attr}")
                
    print("Available constants:")
    for attr in sorted(dir(geodesy)):
        if attr.isupper():
            print(f"  geodesy.{attr}")
            
except Exception as e:
    print(f"Error testing GeoPoint: {e}")

# Create a LocalGeoCS instance to inspect its methods
sfm_constraints = SFMConstraints()
local_geo_cs = sfm_constraints.local_geo_cs

print("LocalGeoCS type:", type(local_geo_cs))
print("Available methods and attributes:")
for attr in sorted(dir(local_geo_cs)):
    if not attr.startswith('_'):
        print(f"  {attr}")

# Check what's available in kwiver.vital.types
print(f"\nChecking kwiver.vital.types for geo conversion functions:")
for attr in sorted(dir(vt)):
    if 'geo' in attr.lower() or 'local' in attr.lower() or 'convert' in attr.lower():
        print(f"  {attr}")

# Try to find geo conversion functionality
try:
    from kwiver.vital import geo_conversion
    print(f"\nFound geo_conversion module")
    for attr in sorted(dir(geo_conversion)):
        if not attr.startswith('_'):
            print(f"  {attr}")
except ImportError:
    print(f"\nNo geo_conversion module found")

# Check if there are any conversion algorithms available
try:
    from kwiver.vital import algo
    print(f"\nChecking kwiver.vital.algo:")
    for attr in sorted(dir(algo)):
        if 'geo' in attr.lower() or 'convert' in attr.lower():
            print(f"  {attr}")
except ImportError:
    print(f"\nNo algo module found")

# Check geo_conv specifically
print(f"\nChecking geo_conv:")
try:
    geo_conv = vt.geo_conv
    print(f"geo_conv type: {type(geo_conv)}")
    for attr in sorted(dir(geo_conv)):
        if not attr.startswith('_'):
            print(f"  {attr}")
except Exception as e:
    print(f"Error accessing geo_conv: {e}")

# Check LocalCartesian too
print(f"\nChecking LocalCartesian:")
try:
    local_cart = vt.LocalCartesian
    print(f"LocalCartesian type: {type(local_cart)}")
    for attr in sorted(dir(local_cart)):
        if not attr.startswith('_'):
            print(f"  {attr}")
            
    # Test creating a LocalCartesian instance
    print(f"\nTesting LocalCartesian instance:")
    lc_instance = vt.LocalCartesian()
    print(f"Instance methods:")
    for attr in sorted(dir(lc_instance)):
        if not attr.startswith('_'):
            print(f"  {attr}")
            
except Exception as e:
    print(f"Error accessing LocalCartesian: {e}")

# Also check what geo_conv function does
print(f"\nTesting geo_conv function:")
try:
    print(f"geo_conv callable: {callable(vt.geo_conv)}")
    # Try to see what geo_conv does - it might return a converter
    help_str = help(vt.geo_conv)
    print(f"geo_conv help: {help_str}")
except Exception as e:
    print(f"Error with geo_conv: {e}")