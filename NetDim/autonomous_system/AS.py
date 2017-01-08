# NetDim
# Copyright (C) 2016 Antoine Fourmy (antoine.fourmy@gmail.com)
# Released under the GNU General Public License GPLv3

import tkinter as tk
from tkinter import ttk
from pythonic_tkinter.preconfigured_widgets import *
from collections import defaultdict
from miscellaneous.network_functions import mac_comparer
from heapq import heappop, heappush
from . import area
from . import AS_management

class AutonomousSystem(object):
    
    class_type = 'AS'
    has_area = False

    def __init__(
                 self, 
                 scenario,
                 name, 
                 id,
                 trunks = set(), 
                 nodes = set(), 
                 imp = False
                 ):
        self.cs = scenario
        self.ntw = self.cs.ntw
        self.name = name
        self.id = id
        self.trunks = trunks
        self.nodes = nodes

        # pAS as in 'pool AS': same as pool network
        self.pAS = {'trunk': self.trunks, 'node': self.nodes}
        
        # unselect everything
        scenario.unhighlight_all()
        
    def __repr__(self):
        return self.name
        
    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        return hash(self.name)
        
    def add_to_AS(self, *objects):
        for obj in objects:
            # add objects in the AS corresponding pool
            self.pAS[obj.type].add(obj)
        
    def remove_from_AS(self, *objects):
        for obj in objects:
            # we remove the object from its pool in the AS
            self.pAS[obj.type].discard(obj)
            # we pop the AS from the dict of object AS, and retrieve the list
            # of area it belongs to in this AS
            obj.AS.pop(self)
            
class ASWithArea(AutonomousSystem):
    
    has_area = True
    
    def __init__(self, *args):
        super().__init__(*args)
        
        # areas is a dict associating a name to an area
        self.areas = {}
        
    def area_factory(self, name, id=0, trunks=set(), nodes=set()):
        if name not in self.areas:
            self.areas[name] = area.Area(name, id, self, trunks, nodes)
        return self.areas[name]
        
    def add_to_area(self, area='Backbone', *objects):
        area.add_to_area(*objects)         
                
    def remove_from_area(self, *objects):
        for obj in objects:
            # for each area, we delete the object from the corresponding pool
            for area in set(obj.AS[self]):
                area.remove_from_area(obj)
        
    def delete_area(self, area):
        # we remove the area of the AS areas dictionary
        area = self.areas.pop(area.name)
        for obj_type in ('node', 'trunk'):
            for obj in area.pa[obj_type]:
                # we remove the area to the list of area in the AS 
                # dictionary, for all objects of the area
                obj.AS[area.AS].remove(area)
            
class Ethernet_AS(AutonomousSystem):
    
    layer = 'Ethernet'
    
    def __init__(self, *args):
        super().__init__(*args)
        
    def add_to_AS(self, *objects):
        super(Ethernet_AS, self).add_to_AS(*objects)
        
class VLAN_AS(ASWithArea, Ethernet_AS):
    
    AS_type = 'VLAN'
    
    def __init__(self, *args):
        super().__init__(*args)
        is_imported = args[-1]
        
        # management window of the AS 
        self.management = AS_management.VLAN_Management(self, is_imported)
                
        if not is_imported:
            # set the default per-AS properties of all AS objects
            self.add_to_AS(*(self.nodes | self.trunks))

        # update the AS management panel by filling all boxes
        self.management.refresh_display()
            
class STP_AS(Ethernet_AS):
    
    AS_type = 'STP'
    
    def __init__(self, *args):
        super().__init__(*args)
        is_imported = args[-1]
        
        # root of the AS
        self.root = None
        self.SPT_trunks = set()
        
        # management window of the AS 
        self.management = AS_management.STP_Management(self, is_imported)
                
        if not is_imported:
            # set the default per-AS properties of all AS objects
            self.add_to_AS(*(self.nodes | self.trunks))
            
        # trigger the root switch election. The root is the swith with the
        # highest priority, or in case of tie, the highest MAC address
        self.root_election()
        # update the AS management panel by filling all boxes
        self.management.refresh_display()
                    
    def add_to_AS(self, *objects):
        super(Ethernet_AS, self).add_to_AS(*objects)       
        
        for obj in objects:
            # A RSTP AS has no area, each object's area set is initialized 
            # to None as it should never be needed
            obj.AS[self] = None
            if obj.type == 'trunk':
                obj.interfaceS(self.name, 'cost', 1)
                obj.interfaceD(self.name, 'cost', 1)
                obj.interfaceS(self.name, 'priority', 32768)
                obj.interfaceD(self.name, 'priority', 32768)
                
            if obj.subtype == 'switch':
                obj.AS_properties[self.name].update({'priority': 32768})
                
    def root_election(self):
        for node in self.nodes:
            if not self.root:
                self.root = node
                continue
            root_priority = self.root.AS_properties[self.name]['priority']
            node_priority = node.AS_properties[self.name]['priority'] 
            # if the current node has a higher priority, it becomes root
            if node_priority < root_priority:
                self.root = node
            # if the priority is the same
            if node_priority == root_priority:
                # and the current node has a higher MAC address, it becomes root
                if mac_comparer(self.root.base_macaddress, node.base_macaddress):
                    self.root = node
        print(self.root)
        
    def build_SPT(self):
        # clear the current spanning tree trunks
        self.SPT_trunks.clear()
        visited = set()
        # allowed nodes and trunks
        allowed_nodes = self.pAS['node']
        allowed_trunks =  self.pAS['trunk'] - self.ntw.fdtks
        # we keep track of all already visited subnetworks so that we 
        # don't add them more than once to the mapping dict.
        heap = [(0, self.root, [])]
        
        while heap:
            dist, node, path_trunk = heappop(heap)
            if node not in visited:
                print(node, dist, path_trunk)
                if path_trunk:
                    self.SPT_trunks.add(path_trunk[-1])
                visited.add(node)
                for neighbor, l2vc in self.ntw.graph[node.id]['l2vc']:
                    adj_trunk = l2vc('link', node)
                    remote_trunk = l2vc('link', neighbor)
                    if adj_trunk in path_trunk:
                        continue
                    # excluded and allowed nodes
                    if neighbor not in allowed_nodes:
                        continue
                    # excluded and allowed trunks
                    if adj_trunk not in allowed_trunks: 
                        continue
                    heappush(heap, (dist + adj_trunk('cost', node), 
                                        neighbor, path_trunk + [adj_trunk]))
    
class IP_AS(AutonomousSystem):
    
    layer = 'IP'
    
    def __init__(self, *args):
        super().__init__(*args)
        
    def add_to_AS(self, *objects):
        super(IP_AS, self).add_to_AS(*objects)
        
        for obj in objects:            
            if obj.subtype == 'router':
                obj.AS_properties[self.name].update({
                                                    'LB_paths': 4,
                                                    'router_id': None
                                                    })
                                                    
    def build_RFT(self):
        allowed_nodes = self.nodes
        allowed_trunks =  self.trunks - self.ntw.fdtks
        for node in self.nodes:
            self.RFT_builder(node, allowed_nodes, allowed_trunks)
                
class RIP_AS(IP_AS):
    
    AS_type = 'RIP'
    
    def __init__(self, *args):
        super().__init__(*args)
        is_imported = args[-1]
        
        # management window of the AS 
        self.management = AS_management.RIP_Management(self, is_imported)
        
        # the metric used to compute the shortest path. By default, it is 
        # a hop count for a RIP AS, and bandwidth-dependent for ISIS or OSPF.
        # if the metric is bandwidth, it is calculated based on the interface
        # of the trunk, and a user-defined reference bandwidth.
        self.metric = 'hop count'
        
        if not is_imported:
            # set the default per-AS properties of all AS objects
            self.add_to_AS(*(self.nodes | self.trunks))
            
        # update the AS management panel by filling all boxes
        self.management.refresh_display()
            
    def add_to_AS(self, *objects):
        super(RIP_AS, self).add_to_AS(*objects)       
        
        for obj in objects:
            # A RIP AS has no area, each object's area set is initialized 
            # to None as it should never be needed
            obj.AS[self] = None
            if obj.type == 'trunk':
                obj.interfaceS(self.name, 'cost', 1)
                obj.interfaceD(self.name, 'cost', 1)   
        
    def RFT_builder(self, source, allowed_nodes, allowed_trunks):
        K = source.AS_properties[self.name]['LB_paths']
        visited = set()
        # we keep track of all already visited subnetworks so that we 
        # don't add them more than once to the mapping dict.
        visited_subnetworks = set()
        heap = [(0, source, [], None)]
        # cost of the shortesth path to a subnetwork
        SP_cost = {}
        
        while heap:
            dist, node, path_trunk, ex_int = heappop(heap)  
            if (node, ex_int) not in visited:
                visited.add((node, ex_int))
                for neighbor, l3vc in self.ntw.graph[node.id]['l3vc']:
                    adj_trunk = l3vc('link', node)
                    remote_trunk = l3vc('link', neighbor)
                    if adj_trunk in path_trunk:
                        continue
                    # excluded and allowed nodes
                    if neighbor not in allowed_nodes:
                        continue
                    # excluded and allowed trunks
                    if adj_trunk not in allowed_trunks: 
                        continue
                    if node == source:
                        ex_ip = remote_trunk('ipaddress', neighbor)
                        ex_int = adj_trunk('interface', source)
                        source.rt[adj_trunk.sntw] = {('C', ex_ip, ex_int,
                                            dist, neighbor, adj_trunk)}
                        SP_cost[adj_trunk.sntw] = 0
                    heappush(heap, (dist + adj_trunk('cost', node), 
                            neighbor, path_trunk + [adj_trunk], ex_int))
                    
            if path_trunk:
                trunk = path_trunk[-1]
                ex_tk = path_trunk[0]
                nh = ex_tk.destination if ex_tk.source == source else ex_tk.source
                ex_ip = ex_tk('ipaddress', nh)
                ex_int = ex_tk('interface', source)
                if trunk.sntw not in source.rt:
                    SP_cost[trunk.sntw] = dist
                    source.rt[trunk.sntw] = {('R', ex_ip, ex_int, 
                                                dist, nh, ex_tk)}
                else:
                    if (dist == SP_cost[trunk.sntw] 
                        and K > len(source.rt[trunk.sntw])):
                        source.rt[trunk.sntw].add(('R', ex_ip, ex_int, 
                                                dist, nh, ex_tk))
        
class ISIS_AS(ASWithArea, IP_AS):
    
    AS_type = 'ISIS'
    
    def __init__(self, *args):
        super().__init__(*args)
        is_imported = args[-1]
        self.ref_bw = 10000 # (kbps)
        
        # management window of the AS 
        self.management = AS_management.ISIS_Management(self, is_imported)
        
        # contains all L1/L2 nodes
        self.border_routers = set()
        
        if not is_imported:
            self.area_factory(
                              'Backbone', 
                              id = 2, 
                              trunks = self.trunks, 
                              nodes = self.nodes
                              )
                              
        # set the default per-AS properties of all AS objects
        self.add_to_AS(*(self.nodes | self.trunks))
        self.add_to_area(self.areas['Backbone'], *(self.nodes | self.trunks))
        
        # update the AS management panel by filling all boxes
        self.management.refresh_display()
        
    def add_to_AS(self, *objects):
        super(ISIS_AS, self).add_to_AS(*objects)       
        
        for obj in objects:
            if obj.type == 'trunk':
                cost = self.ref_bw / obj.bw
                obj.interfaceS(self.name, 'cost', cost)
                obj.interfaceD(self.name, 'cost', cost)     

    def RFT_builder(self, source, allowed_nodes, allowed_trunks):

        K = source.AS_properties[self.name]['LB_paths']
        visited = set()
        # we keep track of all already visited subnetworks so that we 
        # don't add them more than once to the mapping dict.
        visited_subnetworks = set()
        heap = [(0, source, [], None)]
        # source area: we make sure that if the node is connected to an area,
        # the path we find to any subnetwork in that area is an intra-area path.
        src_areas = source.AS[self]
        # cost of the shortesth path to a subnetwork
        SP_cost = {}
                
        # if source is an L1 there will be a default route to
        # 0.0.0.0 heading to the closest L1/L2 node.
        src_area ,= source.AS[self]
        
        # we keep a boolean telling us if source is L1 so that we know we
        # must add the i*L1 default route when we first meet a L1/L2 node
        # and all other routes are i L1 as rtype (route type).
        isL1 = source not in self.border_routers and src_area.name != 'Backbone'
        
        while heap:
            dist, node, path_trunk, ex_int = heappop(heap)  
            if (node, ex_int) not in visited:
                visited.add((node, ex_int))
                for neighbor, l3vc in self.ntw.graph[node.id]['l3vc']:
                    adj_trunk = l3vc('link', node)
                    remote_trunk = l3vc('link', neighbor)
                    if adj_trunk in path_trunk:
                        continue
                    # excluded and allowed nodes
                    if neighbor not in allowed_nodes:
                        continue
                    # excluded and allowed trunks
                    if adj_trunk not in allowed_trunks: 
                        continue
                    if node == source:
                        ex_ip = remote_trunk('ipaddress', neighbor)
                        ex_int = adj_trunk('interface', source)
                        source.rt[adj_trunk.sntw] = {('C', ex_ip, ex_int,
                                            dist, neighbor, adj_trunk)}
                        SP_cost[adj_trunk.sntw] = 0
                    heappush(heap, (dist + adj_trunk('cost', node), 
                            neighbor, path_trunk + [adj_trunk], ex_int))
                    
            if path_trunk:
                trunk = path_trunk[-1]
                ex_tk = path_trunk[0]
                nh = ex_tk.destination if ex_tk.source == source else ex_tk.source
                ex_ip = ex_tk('ipaddress', nh)
                ex_int = ex_tk('interface', source)
                if isL1:
                    if (node in self.border_routers 
                                        and '0.0.0.0' not in source.rt):
                        source.rt['0.0.0.0'] = {('i*L1', ex_ip, ex_int,
                                                    dist, nh, ex_tk)}
                    else:
                        if (('i L1', trunk.sntw) not in visited_subnetworks 
                                        and trunk.AS[self] & ex_tk.AS[self]):
                            visited_subnetworks.add(('i L1', trunk.sntw))
                            source.rt[trunk.sntw] = {('i L1', ex_ip, ex_int,
                                    dist + trunk('cost', node), nh, ex_tk)}
                else:
                    trunkAS ,= trunk.AS[self]
                    exit_area ,= ex_tk.AS[self]
                    rtype = 'i L1' if (trunk.AS[self] & ex_tk.AS[self] and 
                                    trunkAS.name != 'Backbone') else 'i L2'
                    # we favor intra-area routes by excluding a 
                    # route if the area of the exit trunk is not
                    # the one of the subnetwork
                    if (not ex_tk.AS[self] & trunk.AS[self] 
                                    and trunkAS.name == 'Backbone'):
                        continue
                    # if the source is an L1/L2 node and the destination
                    # is an L1 area different from its own, we force it
                    # to use the backbone by forbidding it to use the
                    # exit interface in the source area
                    if (rtype == 'i L2' and source in self.border_routers and 
                                exit_area.name != 'Backbone'):
                        continue
                    if (('i L1', trunk.sntw) not in visited_subnetworks 
                        and ('i L2', trunk.sntw) not in visited_subnetworks):
                        visited_subnetworks.add((rtype, trunk.sntw))
                        source.rt[trunk.sntw] = {(rtype, ex_ip, ex_int,
                                dist + trunk('cost', node), nh, ex_tk)}
                    # TODO
                    # IS-IS uses per-address unequal cost load balancing 
                    # a user-defined variance defined as a percentage of the
                    # primary path cost defines which paths can be used
                    # (up to 9).
                
class OSPF_AS(ASWithArea, IP_AS):
    
    AS_type = 'OSPF'
    
    def __init__(self, *args):
        super().__init__(*args)
        is_imported = args[-1]
        self.metric = 'bandwidth'
        self.ref_bw = 10**8

        # management window of the AS
        self.management = AS_management.OSPF_Management(self, is_imported)
        
        # contains all ABRs
        self.border_routers = set()
        
        # node used to exit the domain (ASBR for OSPF)
        self.exit_point = None
        
        if not is_imported:
            self.area_factory(
                              'Backbone', 
                              id = 0, 
                              trunks = self.trunks, 
                              nodes = self.nodes
                              )
                              
            # set the default per-AS properties of all AS objects
            self.add_to_AS(*(self.nodes | self.trunks))
            self.add_to_area(self.areas['Backbone'], *(self.nodes | self.trunks))
            
        # update the AS management panel by filling all boxes
        self.management.refresh_display()
        
    def add_to_AS(self, *objects):
        super(OSPF_AS, self).add_to_AS(*objects)       
        
        for obj in objects:
            if obj.type == 'trunk':
                cost = self.ref_bw / obj.bw
                obj.interfaceS(self.name, 'cost', cost)
                obj.interfaceD(self.name, 'cost', cost)  
            
    def RFT_builder(self, source, allowed_nodes, allowed_trunks):
        K = source.AS_properties[self.name]['LB_paths']
        visited = set()
        # we keep track of all already visited subnetworks so that we 
        # don't add them more than once to the mapping dict.
        visited_subnetworks = set()
        heap = [(0, source, [], None)]
        # source area: we make sure that if the node is connected to an area,
        # the path we find to any subnetwork in that area is an intra-area path.
        src_areas = source.AS[self]
        # cost of the shortesth path to a subnetwork
        SP_cost = {}
        
        while heap:
            dist, node, path_trunk, ex_int = heappop(heap)  
            if (node, ex_int) not in visited:
                visited.add((node, ex_int))
                for neighbor, l3vc in self.ntw.graph[node.id]['l3vc']:
                    adj_trunk = l3vc('link', node)
                    remote_trunk = l3vc('link', neighbor)
                    if adj_trunk in path_trunk:
                        continue
                    # excluded and allowed nodes
                    if neighbor not in allowed_nodes:
                        continue
                    # excluded and allowed trunks
                    if adj_trunk not in allowed_trunks: 
                        continue
                    if node == source:
                        ex_ip = remote_trunk('ipaddress', neighbor)
                        ex_int = adj_trunk('interface', source)
                        source.rt[adj_trunk.sntw] = {('C', ex_ip, ex_int,
                                            dist, neighbor, adj_trunk)}
                        SP_cost[adj_trunk.sntw] = 0
                    heappush(heap, (dist + adj_trunk('cost', node), 
                            neighbor, path_trunk + [adj_trunk], ex_int))
                    
            if path_trunk:
                trunk = path_trunk[-1]
                ex_tk = path_trunk[0]
                nh = ex_tk.destination if ex_tk.source == source else ex_tk.source
                ex_ip = ex_tk('ipaddress', nh)
                ex_int = ex_tk('interface', source)
                # we check if the trunk has any common area with the
                # exit trunk: if it does not, it is an inter-area route.
                rtype = 'O' if (trunk.AS[self] & ex_tk.AS[self]) else 'O IA'
                if trunk.sntw not in source.rt:
                    SP_cost[trunk.sntw] = dist
                    source.rt[trunk.sntw] = {(rtype, ex_ip, ex_int, 
                                                dist, nh, ex_tk)}
                else:
                    for route in source.rt[trunk.sntw]:
                        break
                    if route[0] == 'O' and rtype == 'IA':
                        continue
                    elif route[0] == 'O IA' and rtype == 'O':
                        SP_cost[trunk.sntw] = dist
                        source.rt[trunk.sntw] = {(rtype, ex_ip, ex_int, 
                                                dist, nh, ex_tk)}
                    else:
                        if (dist == SP_cost[trunk.sntw]
                            and K > len(source.rt[trunk.sntw])):
                            source.rt[trunk.sntw].add((
                                                    rtype, ex_ip, ex_int, 
                                                        dist, nh, ex_tk
                                                        ))
                if (rtype, trunk.sntw) not in visited_subnetworks:
                    if ('O', trunk.sntw) in visited_subnetworks:
                        continue
                    else:
                        visited_subnetworks.add((rtype, trunk.sntw))
                        source.rt[trunk.sntw] = {(rtype, ex_ip, ex_int, 
                                                        dist, nh, ex_tk)}
                                                        
                                    
                    
class ModifyAS(CustomTopLevel):
    def __init__(self, scenario, mode, obj, AS=set()):
        super().__init__()
        # TODO put that in the dict
        titles = {
        'add': 'Add to AS/area', 
        'remove': 'Remove from AS', 
        'remove area': 'Remove from area',
        'manage': 'Manage AS'
        }
        self.title(titles[mode])
        # always at least one row and one column with a weight > 0
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        if mode == 'add':
            command = lambda: self.add(scenario, *obj)
            values = tuple(map(str, scenario.ntw.pnAS.values()))
        elif mode == 'remove':
            values = tuple(map(str, AS))
            command = lambda: self.remove_from_AS(scenario, *obj)
        elif mode == 'remove area':
            values = tuple(map(str, AS))
            command = lambda: self.remove_from_area(scenario, *obj)
        elif mode == 'manage':
            values = tuple(map(str, AS))
            command = lambda: self.manage_AS(scenario)
        
        # List of existing AS
        self.AS_list = ttk.Combobox(self, width=9)
        self.AS_list['values'] = values
        self.AS_list.current(0)
        self.AS_list.grid(row=0, column=0, columnspan=2, 
                                            pady=5, padx=5, sticky='nsew')
        self.AS_list.bind('<<ComboboxSelected>>', 
                                        lambda e: self.update_value(scenario))
        
        if mode in ('add', 'remove area'):
            self.area_list = ttk.Combobox(self, width=9)
            self.update_value(scenario)
            self.area_list.current(0)
            self.area_list.grid(row=1, column=0, columnspan=2, 
                                            pady=5, padx=5, sticky='nsew')
        
        # Button to add in an AS
        self.button_add_AS = ttk.Button(self, text='OK', command=command)
        #row = 2 if mode in ('add', 'remove area') else 1
        self.button_add_AS.grid(row=2, column=0, columnspan=2, 
                                            pady=5, padx=5, sticky='nsew')
        
    # when a different AS is selected, the area combobox is updated accordingly
    def update_value(self, scenario):
        selected_AS = scenario.ntw.AS_factory(name=self.AS_list.get())
        if selected_AS.has_area:
            self.area_list['values'] = tuple(map(str, selected_AS.areas))
        else:
            self.area_list['values'] = ()
        
    # TODO merge these three functions into one with the mode 
    # they share the check + destroy
    def add(self, scenario, *objects):
        selected_AS = scenario.ntw.AS_factory(name=self.AS_list.get())
        selected_AS.management.add_to_AS(self.area_list.get(), *objects)
        self.destroy()
        
    def remove_from_area(self, scenario, *objects):
        selected_AS = scenario.ntw.AS_factory(name=self.AS_list.get())
        selected_AS.management.remove_from_area(self.area_list.get(), *objects)
        self.destroy()
        
    def remove_from_AS(self, scenario, *objects):
        selected_AS = scenario.ntw.AS_factory(name=self.AS_list.get())
        selected_AS.management.remove_from_AS(*objects)
        self.destroy()
        
    def manage_AS(self, scenario):
        selected_AS = scenario.ntw.AS_factory(name=self.AS_list.get())
        selected_AS.management.deiconify()
        self.destroy()
        
        
class ASOperation(CustomTopLevel):
    
    # Add objects to an AS, or remove objects from an AS
    
    def __init__(self, scenario, mode, obj, AS=set()):
        super().__init__()
        
        title = 'Add to AS' if mode == 'add' else 'Remove from AS'
        self.title(title)
        
        if mode == 'add':
            # All AS are proposed 
            values = tuple(map(str, scenario.ntw.pnAS))
            print(values)
        else:
            # Only the common AS among all selected objects
            values = tuple(map(str, AS))
        
        # List of existing AS
        self.AS_list = Combobox(self, width=9)
        self.AS_list['values'] = values
        #self.AS_list.current(0)

        button_add_AS = Button(self)
        button_add_AS.text = 'OK'
        button_add_AS.command = lambda: self.as_operation(scenario, mode, *obj)
        
        self.AS_list.grid(0, 0, 1, 2)
        button_add_AS.grid(1, 0, 1, 2)
        
    def as_operation(self, scenario, mode, *objects):
        selected_AS = scenario.ntw.AS_factory(name=self.AS_list.get())
        print(mode)
        if mode == 'add':
            selected_AS.management.add_to_AS(*objects)
        else:
            selected_AS.management.remove_from_AS(*objects)
        self.destroy()
        
class ASCreation(CustomTopLevel):
    def __init__(self, scenario, nodes, trunks):
        super().__init__()
        self.title('Create AS')
        
        # List of AS type
        self.AS_type_list = Combobox(self, width=10)
        self.AS_type_list['values'] = ('RIP', 'ISIS', 'OSPF', 'RSTP', 'BGP', 'STP', 'VLAN')
        self.AS_type_list.current(0)

        # retrieve and save node data
        button_create_AS = Button(self)
        button_create_AS.text = 'Create AS'
        button_create_AS.command = lambda: self.create_AS(scenario, nodes, trunks)
                        
        # Label for the name/type of the AS
        label_name = Label(self)
        label_name.text = 'Name'
        
        label_type = Label(self)
        label_type.text = 'Type'
        
        label_id = Label(self)
        label_id.text = 'ID'
        
        # Entry box for the name of the AS
        self.entry_name  = Entry(self, width=13)
        self.entry_id  = Entry(self, width=13)
        
        label_name.grid(0, 0)
        label_id.grid(1, 0)
        self.entry_name.grid(0, 1)
        self.entry_id.grid(1, 1)
        label_type.grid(2, 0)
        self.AS_type_list.grid(2, 1)
        button_create_AS.grid(3, 0, 1, 2)

    def create_AS(self, scenario, nodes, trunks):
        # automatic initialization of the AS id in case it is empty
        id = int(self.entry_id.get()) if self.entry_id.get() else len(scenario.ntw.pnAS) + 1
        
        new_AS = scenario.ntw.AS_factory(
                                         self.AS_type_list.get(), 
                                         self.entry_name.get(), 
                                         id,
                                         trunks, 
                                         nodes
                                         )
        self.destroy()
            