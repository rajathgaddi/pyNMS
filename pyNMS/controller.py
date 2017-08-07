# Copyright (C) 2017 Antoine Fourmy <antoine dot fourmy at gmail dot com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from collections import defaultdict, OrderedDict
from objects.objects import *
from os.path import abspath, join, pardir
from graph_algorithms.shortest_path_window import ShortestPathWindow
from graph_algorithms.maximum_flow_window import MaximumFlowWindow
from graph_algorithms.disjoint_sp_window import DisjointSPWindow
from graph_algorithms.minimum_cost_flow_window import MCFlowWindow
from graph_algorithms.rwa_window import RWAWindow
from graph_generation.graph_generation import GraphGenerationWindow
from gis.gis_parameter import GISParameterWindow
from miscellaneous.graph_drawing import *
from miscellaneous.search_window import SearchWindow
from miscellaneous.style_window import StyleWindow
from main_menus import (
                        node_creation_panel,
                        link_creation_panel,
                        node_display_panel,
                        link_display_panel,
                        routing_panel
                        )
from project import Project
from ip_networks.ssh_management import SSHManagementWindow
from views import base_view
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
                         QColor, 
                         QIcon,
                         QDrag, 
                         QPainter, 
                         QPixmap
                         )
from PyQt5.QtWidgets import (
                             QAction,
                             QFrame,
                             QFileDialog,
                             QPushButton, 
                             QMainWindow, 
                             QApplication,
                             QHBoxLayout,
                             QVBoxLayout,
                             QLabel, 
                             QGraphicsPixmapItem,
                             QGroupBox,
                             QTabWidget,
                             QWidget
                             )

class Controller(QMainWindow):
    def __init__(self, path_app):
        super(Controller, self).__init__()
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(212, 212, 212))
        self.setPalette(palette)
        
        # initialize all paths
        self.path_app = path_app
        path_parent = abspath(join(path_app, pardir))
        self.path_icon = join(path_parent, 'Icons')
        self.path_workspace = join(path_parent, 'Workspace')
        self.path_shapefiles = join(path_parent, 'Shapefiles')
        
        # a QMainWindow needs a central widget for the layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        ## permanent windows
        
        self.graph_generation_window = GraphGenerationWindow(self)
        self.spring_layout_parameters_window = SpringLayoutParametersWindow(self)
        self.gis_parameter_window = GISParameterWindow(self)
        self.ssh_management_window = SSHManagementWindow(self)
        self.search_window = SearchWindow(self)
        self.style_window = StyleWindow()
        
        # Graph algorithm windows
        self.shortest_path_window = ShortestPathWindow(self)   
        self.maximum_flow_window = MaximumFlowWindow(self)
        self.disjoint_sp_window = DisjointSPWindow(self)
        self.mcf_window = MCFlowWindow(self)
        self.rwa_window = RWAWindow(self)
        
        ## Menu bar
        menu_bar = self.menuBar()
        
        new_project = QAction('Add project', self)
        new_project.setStatusTip('Create a new project')
        new_project.triggered.connect(self.close)
        
        delete_project = QAction('Delete project', self)
        delete_project.setStatusTip('Delete the current project')
        delete_project.triggered.connect(self.close)
        
        import_project = QAction('Import project', self)
        import_project.setStatusTip('Import a project')
        import_project.triggered.connect(self.import_project)
        
        export_project = QAction('Export project', self)
        export_project.setStatusTip('Export the current project')
        export_project.triggered.connect(self.export_project)
        
        quit_pynms = QAction('Quit', self)
        quit_pynms.setShortcut('Ctrl+Q')
        quit_pynms.setStatusTip('Close pyNMS')
        quit_pynms.triggered.connect(self.close)

        main_menu = menu_bar.addMenu('File')
        main_menu.addAction(new_project)
        main_menu.addAction(delete_project)
        main_menu.addSeparator()
        main_menu.addAction(import_project)
        main_menu.addAction(export_project)
        main_menu.addSeparator()
        main_menu.addAction(quit_pynms)
        
        edit_style = QAction('Styles', self)
        edit_style.setStatusTip('Choose a style for the GUI')
        edit_style.triggered.connect(lambda: self.style_window.show())
        
        main_menu = menu_bar.addMenu('Edit')
        main_menu.addAction(edit_style)
        
        spring_parameters = QAction('Spring layout parameters', self)
        spring_parameters.setStatusTip('Spring layout parameters')
        spring_parameters.triggered.connect(lambda: self.spring_layout_parameters_window.show())
        
        drawing_menu = menu_bar.addMenu('Drawing parameters')
        drawing_menu.addAction(spring_parameters)
        
        show_hide_map = QAction('Show / Hide', self)
        show_hide_map.setStatusTip('Show / Hide map')
        show_hide_map.triggered.connect(self.show_hide_map)
        
        delete_map = QAction('Delete the map', self)
        delete_map.setStatusTip('Delete the map')
        delete_map.triggered.connect(self.delete_map)
        
        GIS_parameters = QAction('GIS parameters', self)
        GIS_parameters.setStatusTip('GIS parameters')
        GIS_parameters.triggered.connect(lambda: self.gis_parameter_window.show())
        
        gis_menu = menu_bar.addMenu('GIS')
        gis_menu.addAction(show_hide_map)
        gis_menu.addAction(delete_map)
        gis_menu.addAction(GIS_parameters)
        
        SP_window = QAction('Shortest path', self)
        SP_window.setStatusTip('Shortest path')
        SP_window.triggered.connect(lambda: self.shortest_path_window.show())
        
        MF_window = QAction('Maximum flow', self)
        MF_window.setStatusTip('Maximum flow')
        MF_window.triggered.connect(lambda: self.maximum_flow_window.show())
        
        DSP_window = QAction('Disjoint shortest paths', self)
        DSP_window.setStatusTip('Disjoint shortest paths')
        DSP_window.triggered.connect(lambda: self.disjoint_sp_window.show())
        
        MCF_window = QAction('Minimum-cost flow', self)
        MCF_window.setStatusTip('Minimum-cost flow')
        MCF_window.triggered.connect(lambda: self.mcf_window.show())
        
        RWA_window = QAction('Routing and wavelength assignment', self)
        RWA_window.setStatusTip('Routing and wavelength assignment')
        RWA_window.triggered.connect(lambda: self.rwa_window.show())
        
        algorithm_menu = menu_bar.addMenu('Advanced algorithms')
        algorithm_menu.addAction(SP_window)
        algorithm_menu.addAction(MF_window)
        algorithm_menu.addAction(DSP_window)
        algorithm_menu.addAction(MCF_window)
        algorithm_menu.addAction(RWA_window)

        ## Status bar
        
        self.statusBar()
        
        new_project_icon = QIcon(join(self.path_icon, 'new_project.png'))
        new_project = QAction(new_project_icon, 'New project', self)
        new_project.setStatusTip('Create a new project')
        new_project.triggered.connect(self.add_project)
        
        import_project_icon = QIcon(join(self.path_icon, 'import_project.png'))
        import_project = QAction(import_project_icon, 'Import project', self)
        import_project.setStatusTip('Import an existing project')
        import_project.triggered.connect(self.import_project)
        
        save_project_icon = QIcon(join(self.path_icon, 'save_project.png'))
        save_project = QAction(save_project_icon, 'Export project', self)
        save_project.setShortcut('Ctrl+S')
        save_project.setStatusTip('Export the project')
        save_project.triggered.connect(self.export_project)
        
        selection_icon = QIcon(join(self.path_icon, 'selection.png'))
        selection_mode = QAction(selection_icon, 'Selection mode', self)
        selection_mode.setStatusTip('Switch to selection mode')
        selection_mode.triggered.connect(self.switch_to_selection_mode)
        
        rectangle_icon = QIcon(join(self.path_icon, 'rectangle.png'))
        rectangle = QAction(rectangle_icon, 'Draw a rectangle', self)
        rectangle.setStatusTip('Draw a rectangle')
        rectangle.triggered.connect(self.rectangle)
        
        ellipse_icon = QIcon(join(self.path_icon, 'ellipse.png'))
        ellipse = QAction(ellipse_icon, 'Draw an ellipse', self)
        ellipse.setStatusTip('Draw an ellipse')
        ellipse.triggered.connect(self.ellipse)
        
        add_note_icon = QIcon(join(self.path_icon, 'add_note.png'))
        add_note = QAction(add_note_icon, 'Add note', self)
        add_note.setStatusTip('Add a note')
        add_note.triggered.connect(self.add_note)
        
        network_view_icon = QIcon(join(self.path_icon, 'network_view.png'))
        network_view = QAction(network_view_icon, 'Network view', self)
        network_view.setStatusTip('Switch to network view')
        network_view.triggered.connect(lambda: self.switch_view('network'))
        
        site_view_icon = QIcon(join(self.path_icon, 'site_view.png'))
        site_view = QAction(site_view_icon, 'Site view', self)
        site_view.setStatusTip('Switch to site view')
        site_view.triggered.connect(lambda: self.switch_view('site'))
        
        graph_generation_icon = QIcon(join(self.path_icon, 'ring.png'))
        graph_generation = QAction(graph_generation_icon, 'Graph generation', self)
        graph_generation.setShortcut('Ctrl+G')
        graph_generation.setStatusTip('Generate a graph')
        graph_generation.triggered.connect(lambda: self.graph_generation_window.show())
        
        stop_drawing_icon = QIcon(join(self.path_icon, 'stop.png'))
        stop_drawing = QAction(stop_drawing_icon, 'Stop drawing', self)
        stop_drawing.setStatusTip('Stop the graph drawing algorithm')
        stop_drawing.triggered.connect(lambda: self.stop_drawing())
        
        refresh_icon = QIcon(join(self.path_icon, 'refresh.png'))
        refresh = QAction(refresh_icon, 'Calculate all', self)
        refresh.setStatusTip('Calculate all (routing options + refresh display)')
        refresh.triggered.connect(self.refresh)
        
        search_icon = QIcon(join(self.path_icon, 'search.png'))
        search = QAction(search_icon, 'Search', self)
        search.setShortcut('Ctrl+F')
        search.setStatusTip('Search objects per property value')
        search.triggered.connect(lambda: self.search_window.show())
        
        zoom_in_icon = QIcon(join(self.path_icon, 'zoom_in.png'))
        zoom_in = QAction(zoom_in_icon, 'Zoom in', self)
        zoom_in.setStatusTip('Zoom in')
        zoom_in.triggered.connect(self.zoom_in)
        
        zoom_out_icon = QIcon(join(self.path_icon, 'zoom_out.png'))
        zoom_out = QAction(zoom_out_icon, 'Zoom out', self)
        zoom_out.setStatusTip('Zoom out')
        zoom_out.triggered.connect(self.zoom_out)
        
        toolbar = self.addToolBar('')
        toolbar.resize(1500, 1500)
        toolbar.setIconSize(QtCore.QSize(70, 70))
        toolbar.addAction(new_project)
        toolbar.addAction(import_project)
        toolbar.addAction(save_project)
        toolbar.addSeparator()
        toolbar.addAction(selection_mode)
        toolbar.addAction(rectangle)
        toolbar.addAction(ellipse)
        toolbar.addAction(add_note)
        toolbar.addSeparator()
        toolbar.addAction(network_view)
        toolbar.addAction(site_view)
        toolbar.addSeparator()
        toolbar.addAction(graph_generation)
        toolbar.addAction(stop_drawing)
        toolbar.addSeparator()
        toolbar.addAction(refresh)
        toolbar.addSeparator()
        toolbar.addAction(search)
        toolbar.addSeparator()
        toolbar.addAction(zoom_in)
        toolbar.addAction(zoom_out)
        
        # create all pixmap images for node subtypes
        self.pixmaps = defaultdict(OrderedDict)
        for color in ('default', 'red', 'purple'):
            for subtype in node_subtype:
                path = join(self.path_icon, ''.join((
                                                    color, 
                                                    '_', 
                                                    subtype, 
                                                    '.gif'
                                                    )))
                self.pixmaps[color][subtype] = QPixmap(path)
                
        # associate a project name to a Project object
        self.dict_project = {}
        # project counter
        self.cpt_project = 0
        
        ## notebook containing all menus
        notebook_menu = QTabWidget(self)
        notebook_menu.setFixedSize(350, 800)
        
        # first tab: the creation menu
        creation_menu = QWidget(notebook_menu)
        notebook_menu.addTab(creation_menu, 'Creation')
        
        # creation menus
        self.node_creation_menu = node_creation_panel.NodeCreationPanel(self)
        self.link_creation_menu = link_creation_panel.LinkCreationPanel(self)
        
        # layout of the creation menu
        creation_menu_layout = QVBoxLayout(creation_menu)
        creation_menu_layout.addWidget(self.node_creation_menu)
        creation_menu_layout.addWidget(self.link_creation_menu)
        
        # second tab: the routing menu
        routing_menu = QWidget(notebook_menu)
        notebook_menu.addTab(routing_menu, 'Routing')
        
        # routing panel
        self.routing_panel = routing_panel.RoutingPanel(self)
        routing_menu_layout = QVBoxLayout(routing_menu)
        routing_menu_layout.addWidget(self.routing_panel)
        
        # third tab: the display menu
        display_menu = QWidget(notebook_menu)
        notebook_menu.addTab(display_menu, 'Display')
        
        # display menus
        self.node_display_menu = node_display_panel.NodeDisplayPanel(self)
        self.link_display_menu = link_display_panel.LinkDisplayPanel(self)
        
        display_menu_layout = QVBoxLayout(display_menu)
        display_menu_layout.addWidget(self.node_display_menu)
        display_menu_layout.addWidget(self.link_display_menu)
        
        ## notebook containing all projects
        self.notebook_project = QTabWidget(self)
        
        # first project
        self.add_project()

        layout = QHBoxLayout(central_widget)
        layout.addWidget(notebook_menu) 
        layout.addWidget(self.notebook_project)
        
        # mode (creation of links or selection of objects)
        # since the drag & drop system for node creation does not interfere 
        # with the selection process, nodes can be created in selection mode
        # OTOH, creating links will automatically switch the mode to creation
        self.mode = 'selection'
        # creation mode (node subtype or link subtype)
        self.creation_mode = 'router'
        
    def add_project(self, name=None):
        self.cpt_project += 1
        if not name:
            name = ' '.join(('project', str(self.cpt_project)))
        new_project = Project(self, name)
        self.notebook_project.addTab(new_project, name)
        self.dict_project[name] = new_project
        return new_project
        
    def import_project(self):
        self.current_project.import_project()
        
    def export_project(self):
        self.current_project.export_project()
        
    def stop_drawing(self):
        self.current_project.current_view.stop_timer()
        
    def switch_to_selection_mode(self):
        self.mode = 'selection'
        
    def switch_view(self, view_mode):
        self.current_project.switch_view(view_mode)
        
    def generate_graph(self):
        self.current_project.generate_graph()

    def close(self):
        pass

        
    def show_hide_map(self):
        self.current_project.current_view.world_map.show_hide_map()
        
    def delete_map(self):
        self.current_project.current_view.world_map.delete_map()
        
    def refresh(self):
        self.current_project.refresh()
        
    def add_note(self):
        pass
        
    def rectangle(self):
        pass
        
    def ellipse(self):
        pass
        
    def zoom_in(self):
        self.current_project.current_view.zoom_in()
        
    def zoom_out(self):
        self.current_project.current_view.zoom_out()