from vtkmodules.vtkFiltersSources import vtkConeSource
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
)


def setup_vtk_cone_pipeline():
    """
    Sets up the VTK pipeline for a cone source.
    Returns the vtkRenderWindow.
    """
    cone_source = vtkConeSource()
    cone_source.SetResolution(12)
    cone_source.SetHeight(3.0)
    cone_source.SetRadius(1.0)
    cone_source.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(cone_source.GetOutputPort())

    actor = vtkActor()
    actor.SetMapper(mapper)

    renderer = vtkRenderer()
    renderer.AddActor(actor)
    renderer.ResetCamera()
    renderer.SetBackground(0.1, 0.2, 0.3)

    render_window = vtkRenderWindow()
    render_window.AddRenderer(renderer)

    return render_window
