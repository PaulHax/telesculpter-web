"""Unit tests for frustum-ground intersection calculations"""

import unittest
import numpy as np

from .kwiver_vtk_util import (
    compute_frustum_ground_intersection,
    get_frustum_planes,
    create_vtk_camera_from_simple_camera,
    VtkCameraBundle
)
from vtkmodules.vtkRenderingCore import vtkCamera
from vtkmodules.vtkCommonDataModel import vtkPlanes
from vtkmodules.vtkFiltersSources import vtkFrustumSource


class TestFrustumGroundIntersection(unittest.TestCase):
    """Test cases for compute_frustum_ground_intersection function"""
    
    def create_test_frustum_planes(self, camera_pos, look_dir, up_dir, fov_deg=45, near=0.1, far=100):
        """Create frustum planes from camera parameters"""
        # Create a VTK camera
        vtk_camera = vtkCamera()
        
        # Set position and orientation
        vtk_camera.SetPosition(camera_pos[0], camera_pos[1], camera_pos[2])
        
        # Calculate focal point
        focal_point = [
            camera_pos[0] + look_dir[0],
            camera_pos[1] + look_dir[1], 
            camera_pos[2] + look_dir[2]
        ]
        vtk_camera.SetFocalPoint(focal_point[0], focal_point[1], focal_point[2])
        vtk_camera.SetViewUp(up_dir[0], up_dir[1], up_dir[2])
        
        # Set camera parameters
        vtk_camera.SetViewAngle(fov_deg)
        vtk_camera.SetClippingRange(near, far)
        
        # Create camera bundle and get frustum planes
        camera_bundle = VtkCameraBundle(camera=vtk_camera, aspect_ratio=1.0)
        return get_frustum_planes(camera_bundle)
        
    def test_camera_looking_straight_down(self):
        """Test camera looking straight down from above"""
        # Camera at height 50, looking straight down
        camera_pos = [0, 0, 50]
        look_dir = [0, 0, -1]  # Looking down
        up_dir = [0, 1, 0]     # Y is up in camera space
        
        frustum_planes = self.create_test_frustum_planes(
            camera_pos, look_dir, up_dir, fov_deg=60, near=1, far=100
        )
        
        result = compute_frustum_ground_intersection(frustum_planes, ground_z=0.0)
        
        # Should have intersection since camera is looking down at ground
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result), 3)  # Valid polygon
        
        # All intersection points should be at ground level
        for point in result:
            self.assertAlmostEqual(point[2], 0.0, places=5)
            
        # Points should be roughly centered around camera X,Y position
        xs = [p[0] for p in result]
        ys = [p[1] for p in result]
        center_x = np.mean(xs)
        center_y = np.mean(ys)
        self.assertAlmostEqual(center_x, 0.0, delta=1.0)
        self.assertAlmostEqual(center_y, 0.0, delta=1.0)
        
    def test_camera_looking_up(self):
        """Test camera looking up (should have no ground intersection)"""
        # Camera at ground level, looking up
        camera_pos = [0, 0, 1]
        look_dir = [0, 0, 1]   # Looking up
        up_dir = [0, 1, 0]
        
        frustum_planes = self.create_test_frustum_planes(
            camera_pos, look_dir, up_dir, fov_deg=45, near=0.1, far=50
        )
        
        result = compute_frustum_ground_intersection(frustum_planes, ground_z=0.0)
        
        # Should have no intersection since camera is looking up
        self.assertIsNone(result)
        
    def test_camera_at_angle(self):
        """Test camera at 45-degree angle"""
        # Camera positioned to look down at 45-degree angle
        camera_pos = [0, -20, 20]
        look_dir = [0, 1, -1]   # Looking forward and down
        look_dir = look_dir / np.linalg.norm(look_dir)  # Normalize
        up_dir = [0, 0, 1]      # Z up
        
        frustum_planes = self.create_test_frustum_planes(
            camera_pos, look_dir, up_dir, fov_deg=60, near=1, far=50
        )
        
        result = compute_frustum_ground_intersection(frustum_planes, ground_z=0.0)
        
        # Should have intersection
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result), 3)
        
        # All points at ground level
        for point in result:
            self.assertAlmostEqual(point[2], 0.0, places=5)
            
    def test_custom_ground_height(self):
        """Test intersection with custom ground plane height"""
        # Camera looking down at custom ground level
        camera_pos = [0, 0, 30]
        look_dir = [0, 0, -1]
        up_dir = [0, 1, 0]
        
        frustum_planes = self.create_test_frustum_planes(
            camera_pos, look_dir, up_dir, fov_deg=45, near=1, far=50
        )
        
        # Test intersection with ground at z=10
        result = compute_frustum_ground_intersection(frustum_planes, ground_z=10.0)
        
        self.assertIsNotNone(result)
        
        # All points should be at custom ground level
        for point in result:
            self.assertAlmostEqual(point[2], 10.0, places=5)
            
    def test_horizontal_camera(self):
        """Test camera oriented horizontally"""
        # Camera looking horizontally (may intersect ground depending on height)
        camera_pos = [0, 0, 5]    # 5 units above ground
        look_dir = [1, 0, -0.2]   # Looking mostly horizontal, slightly down
        look_dir = look_dir / np.linalg.norm(look_dir)
        up_dir = [0, 0, 1]
        
        frustum_planes = self.create_test_frustum_planes(
            camera_pos, look_dir, up_dir, fov_deg=90, near=1, far=100
        )
        
        result = compute_frustum_ground_intersection(frustum_planes, ground_z=0.0)
        
        # Should have intersection due to wide FOV and slight downward angle
        self.assertIsNotNone(result)
        
    def test_camera_close_to_ground(self):
        """Test camera very close to ground"""
        # Camera just above ground, looking at shallow angle
        camera_pos = [0, 0, 2]
        look_dir = [1, 0, -0.1]   # Very shallow angle
        look_dir = look_dir / np.linalg.norm(look_dir)
        up_dir = [0, 0, 1]
        
        frustum_planes = self.create_test_frustum_planes(
            camera_pos, look_dir, up_dir, fov_deg=120, near=0.5, far=50
        )
        
        result = compute_frustum_ground_intersection(frustum_planes, ground_z=0.0)
        
        # Should have intersection due to wide FOV
        self.assertIsNotNone(result)
        
        # Calculate footprint area (should be large due to shallow angle)
        if result and len(result) >= 3:
            # Simple polygon area calculation using shoelace formula
            area = 0
            n = len(result)
            for i in range(n):
                j = (i + 1) % n
                area += result[i][0] * result[j][1]
                area -= result[j][0] * result[i][1]
            area = abs(area) / 2
            self.assertGreater(area, 10)  # Should be reasonably large
            
    def test_different_fov_angles(self):
        """Test different field of view angles"""
        camera_pos = [0, 0, 20]
        look_dir = [0, 0, -1]
        up_dir = [0, 1, 0]
        
        # Test narrow FOV
        frustum_planes_narrow = self.create_test_frustum_planes(
            camera_pos, look_dir, up_dir, fov_deg=15, near=1, far=50
        )
        result_narrow = compute_frustum_ground_intersection(frustum_planes_narrow, ground_z=0.0)
        
        # Test wide FOV
        frustum_planes_wide = self.create_test_frustum_planes(
            camera_pos, look_dir, up_dir, fov_deg=120, near=1, far=50
        )
        result_wide = compute_frustum_ground_intersection(frustum_planes_wide, ground_z=0.0)
        
        # Both should have intersections
        self.assertIsNotNone(result_narrow)
        self.assertIsNotNone(result_wide)
        
        # Wide FOV should produce larger footprint
        def polygon_area(points):
            if len(points) < 3:
                return 0
            area = 0
            n = len(points)
            for i in range(n):
                j = (i + 1) % n
                area += points[i][0] * points[j][1]
                area -= points[j][0] * points[i][1]
            return abs(area) / 2
            
        area_narrow = polygon_area(result_narrow)
        area_wide = polygon_area(result_wide)
        
        self.assertGreater(area_wide, area_narrow)
        
    def test_frustum_edge_cases(self):
        """Test edge cases and boundary conditions"""
        # Camera with near plane at ground level
        camera_pos = [0, 0, 5]
        look_dir = [0, 0, -1]
        up_dir = [0, 1, 0]
        
        # Very small clipping range
        frustum_planes = self.create_test_frustum_planes(
            camera_pos, look_dir, up_dir, fov_deg=45, near=4.9, far=5.1
        )
        
        result = compute_frustum_ground_intersection(frustum_planes, ground_z=0.0)
        
        # Should still work (camera sees ground through frustum)
        self.assertIsNotNone(result)
        
    def test_polygon_ordering(self):
        """Test that intersection polygon vertices are properly ordered"""
        camera_pos = [0, 0, 20]
        look_dir = [0, 0, -1]
        up_dir = [0, 1, 0]
        
        frustum_planes = self.create_test_frustum_planes(
            camera_pos, look_dir, up_dir, fov_deg=60, near=1, far=50
        )
        
        result = compute_frustum_ground_intersection(frustum_planes, ground_z=0.0)
        
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result), 3)
        
        # Check that vertices form a reasonable polygon
        # (no duplicate points, reasonable distances between consecutive points)
        for i in range(len(result)):
            j = (i + 1) % len(result)
            p1 = np.array(result[i])
            p2 = np.array(result[j])
            dist = np.linalg.norm(p2 - p1)
            
            self.assertGreater(dist, 0.01)  # No duplicates/very close points
            self.assertLess(dist, 1000)     # Not wildly separated
            
    def test_symmetric_footprint(self):
        """Test that symmetric camera setup produces symmetric footprint"""
        # Camera looking straight down should produce symmetric footprint
        camera_pos = [0, 0, 25]
        look_dir = [0, 0, -1]
        up_dir = [0, 1, 0]
        
        frustum_planes = self.create_test_frustum_planes(
            camera_pos, look_dir, up_dir, fov_deg=90, near=1, far=50
        )
        
        result = compute_frustum_ground_intersection(frustum_planes, ground_z=0.0)
        
        self.assertIsNotNone(result)
        
        # Check approximate symmetry around origin
        xs = [p[0] for p in result]
        ys = [p[1] for p in result]
        
        # Centroid should be near camera position (0,0)
        centroid_x = np.mean(xs)
        centroid_y = np.mean(ys)
        
        self.assertAlmostEqual(centroid_x, 0.0, delta=1.0)
        self.assertAlmostEqual(centroid_y, 0.0, delta=1.0)
        
        # Should have roughly equal extents in X and Y directions
        x_extent = max(xs) - min(xs)
        y_extent = max(ys) - min(ys)
        
        # Allow 10% difference for numerical precision
        self.assertAlmostEqual(x_extent, y_extent, delta=max(x_extent, y_extent) * 0.1)


class TestFrustumPlaneGeneration(unittest.TestCase):
    """Test VTK frustum plane generation itself"""
    
    def test_frustum_planes_format(self):
        """Test that frustum planes are in expected format"""
        # Create simple camera
        vtk_camera = vtkCamera()
        vtk_camera.SetPosition(0, 0, 10)
        vtk_camera.SetFocalPoint(0, 0, 0)
        vtk_camera.SetViewUp(0, 1, 0)
        vtk_camera.SetViewAngle(45)
        vtk_camera.SetClippingRange(1, 50)
        
        camera_bundle = VtkCameraBundle(camera=vtk_camera, aspect_ratio=1.0)
        planes = get_frustum_planes(camera_bundle)
        
        # Should have 24 coefficients (6 planes * 4 coefficients each)
        self.assertEqual(len(planes), 24)
        
        # All coefficients should be finite numbers
        for coeff in planes:
            self.assertTrue(np.isfinite(coeff))
            
    def test_vtk_frustum_source_integration(self):
        """Test integration with VTK's frustum source"""
        # Create test frustum planes
        vtk_camera = vtkCamera()
        vtk_camera.SetPosition(0, 0, 20)
        vtk_camera.SetFocalPoint(0, 0, 0)
        vtk_camera.SetViewUp(0, 1, 0)
        vtk_camera.SetViewAngle(60)
        vtk_camera.SetClippingRange(5, 50)
        
        camera_bundle = VtkCameraBundle(camera=vtk_camera, aspect_ratio=1.0)
        planes_coeffs = get_frustum_planes(camera_bundle)
        
        # Create VTK frustum source
        planes_object = vtkPlanes()
        planes_object.SetFrustumPlanes(planes_coeffs)
        
        frustum_source = vtkFrustumSource()
        frustum_source.SetPlanes(planes_object)
        frustum_source.ShowLinesOff()
        frustum_source.Update()
        
        frustum_poly = frustum_source.GetOutput()
        
        # Should have 8 points (frustum corners)
        self.assertEqual(frustum_poly.GetNumberOfPoints(), 8)
        
        # Check that points are reasonable
        for i in range(8):
            pt = frustum_poly.GetPoint(i)
            # All coordinates should be finite
            self.assertTrue(all(np.isfinite(pt)))
            # Z coordinates should be reasonable (camera looking down from z=20)
            self.assertGreaterEqual(pt[2], -50)  # Should be above far plane
            self.assertLessEqual(pt[2], 20)     # Should be below camera


if __name__ == '__main__':
    unittest.main()