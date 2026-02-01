#!/usr/bin/env python3
# encoding: utf-8

# Enhanced version of k8s_mini_internet.py with visualization support
# This demonstrates how to use the Kubernetes compiler with Internet Map visualization

from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService, DomainNameService
from seedemu.compiler import KubernetesCompiler, Platform
from seedemu.core import Emulator, Binding, Filter
import os, sys

def run():
    # Initialize the emulator and layers
    emu     = Emulator()
    base    = Base()
    routing = Routing()
    ebgp    = Ebgp()
    web     = WebService()
    dns     = DomainNameService()

    ###############################################################################
    # Create Internet exchanges 

    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)

    ix100.getPeeringLan().setDisplayName('New York-100')
    ix101.getPeeringLan().setDisplayName('Chicago-101')
    ix102.getPeeringLan().setDisplayName('San Francisco-102')
    ix103.getPeeringLan().setDisplayName('Los Angeles-103')
    ix104.getPeeringLan().setDisplayName('Seattle-104')
    ix105.getPeeringLan().setDisplayName('Miami-105')

    ###############################################################################
    # Create transit ASes

    as2 = base.createAutonomousSystem(2)
    as3 = base.createAutonomousSystem(3)
    as4 = base.createAutonomousSystem(4)
    as11 = base.createAutonomousSystem(11)
    as12 = base.createAutonomousSystem(12)

    ###############################################################################
    # Create stub ASes

    as150 = base.createAutonomousSystem(150)
    as151 = base.createAutonomousSystem(151)
    as152 = base.createAutonomousSystem(152)
    as153 = base.createAutonomousSystem(153)
    as154 = base.createAutonomousSystem(154)
    as160 = base.createAutonomousSystem(160)
    as161 = base.createAutonomousSystem(161)
    as162 = base.createAutonomousSystem(162)
    as163 = base.createAutonomousSystem(163)
    as164 = base.createAutonomousSystem(164)
    as170 = base.createAutonomousSystem(170)
    as171 = base.createAutonomousSystem(171)

    ###############################################################################
    # Create networks and join them to IXes

    # AS2
    as2.createNetwork('net_100_101')
    as2.joinNetwork('net_100_101', ix100)
    as2.joinNetwork('net_100_101', ix101)

    as2.createNetwork('net_101_102')
    as2.joinNetwork('net_101_102', ix101)
    as2.joinNetwork('net_101_102', ix102)

    as2.createNetwork('net_100_105')
    as2.joinNetwork('net_100_105', ix100)
    as2.joinNetwork('net_100_105', ix105)

    # AS3
    as3.createNetwork('net_100_103')
    as3.joinNetwork('net_100_103', ix100)
    as3.joinNetwork('net_100_103', ix103)

    as3.createNetwork('net_100_105')
    as3.joinNetwork('net_100_105', ix100)
    as3.joinNetwork('net_100_105', ix105)

    as3.createNetwork('net_103_105')
    as3.joinNetwork('net_103_105', ix103)
    as3.joinNetwork('net_103_105', ix105)

    as3.createNetwork('net_103_104')
    as3.joinNetwork('net_103_104', ix103)
    as3.joinNetwork('net_103_104', ix104)

    # AS4
    as4.createNetwork('net_100_104')
    as4.joinNetwork('net_100_104', ix100)
    as4.joinNetwork('net_100_104', ix104)

    as4.createNetwork('net_102_104')
    as4.joinNetwork('net_102_104', ix102)
    as4.joinNetwork('net_102_104', ix104)

    # AS11
    as11.createNetwork('net_102_105')
    as11.joinNetwork('net_102_105', ix102)
    as11.joinNetwork('net_102_105', ix105)

    # AS12
    as12.createNetwork('net_101_104')
    as12.joinNetwork('net_101_104', ix101)
    as12.joinNetwork('net_101_104', ix104)

    # Stub ASes
    as150.createNetwork('net0')
    as151.createNetwork('net0')
    as152.createNetwork('net0')
    as153.createNetwork('net0')
    as154.createNetwork('net0')
    as160.createNetwork('net0')
    as161.createNetwork('net0')
    as162.createNetwork('net0')
    as163.createNetwork('net0')
    as164.createNetwork('net0')
    as170.createNetwork('net0')
    as171.createNetwork('net0')

    ###############################################################################
    # Create routers

    # AS2 routers
    as2r100 = as2.createRouter('r100')
    as2r100.joinNetwork('net_100_101')
    as2r100.joinNetwork('net_100_105')

    as2r101 = as2.createRouter('r101')
    as2r101.joinNetwork('net_101_102')
    as2r101.joinNetwork('net_100_101')

    as2r102 = as2.createRouter('r102')
    as2r102.joinNetwork('net_101_102')
    as2r102.joinNetwork('net_100_105')

    as2r105 = as2.createRouter('r105')
    as2r105.joinNetwork('net_100_105')

    # AS3 routers
    as3r100 = as3.createRouter('r100')
    as3r100.joinNetwork('net_100_103')
    as3r100.joinNetwork('net_100_105')

    as3r103 = as3.createRouter('r103')
    as3r103.joinNetwork('net_103_105')
    as3r103.joinNetwork('net_100_103')
    as3r103.joinNetwork('net_103_104')

    as3r104 = as3.createRouter('r104')
    as3r104.joinNetwork('net_103_104')
    as3r104.joinNetwork('net_100_103')

    as3r105 = as3.createRouter('r105')
    as3r105.joinNetwork('net_100_105')
    as3r105.joinNetwork('net_103_105')

    # AS4 routers
    as4r100 = as4.createRouter('r100')
    as4r100.joinNetwork('net_100_104')
    as4r100.joinNetwork('net_102_104')

    as4r102 = as4.createRouter('r102')
    as4r102.joinNetwork('net_102_104')
    as4r102.joinNetwork('net_100_104')

    as4r104 = as4.createRouter('r104')
    as4r104.joinNetwork('net_102_104')

    # AS11 routers
    as11r102 = as11.createRouter('r102')
    as11r102.joinNetwork('net_102_105')

    as11r105 = as11.createRouter('r105')
    as11r105.joinNetwork('net_102_105')

    # AS12 routers
    as12r101 = as12.createRouter('r101')
    as12r101.joinNetwork('net_101_104')

    as12r104 = as12.createRouter('r104')
    as12r104.joinNetwork('net_101_104')

    # Stub AS routers
    as150r0 = as150.createRouter('router0')
    as150r0.joinNetwork('net0')

    as151r0 = as151.createRouter('router0')
    as151r0.joinNetwork('net0')

    as152r0 = as152.createRouter('router0')
    as152r0.joinNetwork('net0')

    as153r0 = as153.createRouter('router0')
    as153r0.joinNetwork('net0')

    as154r0 = as154.createRouter('router0')
    as154r0.joinNetwork('net0')

    as160r0 = as160.createRouter('router0')
    as160r0.joinNetwork('net0')

    as161r0 = as161.createRouter('router0')
    as161r0.joinNetwork('net0')

    as162r0 = as162.createRouter('router0')
    as162r0.joinNetwork('net0')

    as163r0 = as163.createRouter('router0')
    as163r0.joinNetwork('net0')

    as164r0 = as164.createRouter('router0')
    as164r0.joinNetwork('net0')

    as170r0 = as170.createRouter('router0')
    as170r0.joinNetwork('net0')

    as171r0 = as171.createRouter('router0')
    as171r0.joinNetwork('net0')

    ###############################################################################
    # Create hosts and services

    # Web hosts
    as150_web = as150.createHost('web')
    as150_web.joinNetwork('net0', address='10.150.0.71')
    web.install('web150')

    as151_web = as151.createHost('web')
    as151_web.joinNetwork('net0', address='10.151.0.71')
    web.install('web151')

    as152_web = as152.createHost('web')
    as152_web.joinNetwork('net0', address='10.152.0.71')
    web.install('web152')

    as153_web = as153.createHost('web')
    as153_web.joinNetwork('net0', address='10.153.0.71')
    web.install('web153')

    as154_web = as154.createHost('web')
    as154_web.joinNetwork('net0', address='10.154.0.71')
    web.install('web154')

    as160_web = as160.createHost('web')
    as160_web.joinNetwork('net0', address='10.160.0.71')
    web.install('web160')

    as161_web = as161.createHost('web')
    as161_web.joinNetwork('net0', address='10.161.0.71')
    web.install('web161')

    as162_web = as162.createHost('web')
    as162_web.joinNetwork('net0', address='10.162.0.71')
    web.install('web162')

    as163_web = as163.createHost('web')
    as163_web.joinNetwork('net0', address='10.163.0.71')
    web.install('web163')

    as164_web = as164.createHost('web')
    as164_web.joinNetwork('net0', address='10.164.0.71')
    web.install('web164')

    as170_web = as170.createHost('web')
    as170_web.joinNetwork('net0', address='10.170.0.71')
    web.install('web170')

    as171_web = as171.createHost('web')
    as171_web.joinNetwork('net0', address='10.171.0.71')
    web.install('web171')

    # DNS hosts
    as150_dns = as150.createHost('dns')
    as150_dns.joinNetwork('net0', address='10.150.0.72')
    dns.install('dns150')

    as151_dns = as151.createHost('dns')
    as151_dns.joinNetwork('net0', address='10.151.0.72')
    dns.install('dns151')

    as152_dns = as152.createHost('dns')
    as152_dns.joinNetwork('net0', address='10.152.0.72')
    dns.install('dns152')

    as153_dns = as153.createHost('dns')
    as153_dns.joinNetwork('net0', address='10.153.0.72')
    dns.install('dns153')

    as154_dns = as154.createHost('dns')
    as154_dns.joinNetwork('net0', address='10.154.0.72')
    dns.install('dns154')

    as160_dns = as160.createHost('dns')
    as160_dns.joinNetwork('net0', address='10.160.0.72')
    dns.install('dns160')

    as161_dns = as161.createHost('dns')
    as161_dns.joinNetwork('net0', address='10.161.0.72')
    dns.install('dns161')

    as162_dns = as162.createHost('dns')
    as162_dns.joinNetwork('net0', address='10.162.0.72')
    dns.install('dns162')

    as163_dns = as163.createHost('dns')
    as163_dns.joinNetwork('net0', address='10.163.0.72')
    dns.install('dns163')

    as164_dns = as164.createHost('dns')
    as164_dns.joinNetwork('net0', address='10.164.0.72')
    dns.install('dns164')

    as170_dns = as170.createHost('dns')
    as170_dns.joinNetwork('net0', address='10.170.0.72')
    dns.install('dns170')

    as171_dns = as171.createHost('dns')
    as171_dns.joinNetwork('net0', address='10.171.0.72')
    dns.install('dns171')

    ###############################################################################
    # Set up DNS records

    for i in range(150, 172):
        if i == 155 or i == 156 or i == 157 or i == 158 or i == 159:
            continue
        for j in range(150, 172):
            if j == 155 or j == 156 or j == 157 or j == 158 or j == 159:
                continue
            dns.getHostByAsn(i).addZone('as{i}.com'.format(i=i))
            dns.getHostByAsn(i).addRecord('www.as{i}.com'.format(i=i), 'A', '10.{i}.0.71'.format(i=i))
            dns.getHostByAsn(i).addRecord('dns.as{i}.com'.format(i=i), 'A', '10.{i}.0.72'.format(i=i))

    ###############################################################################
    # Set up BGP relationships

    # AS2 relationships
    ebgp.addPrivatePeerings(as2, [as3, as4, as11, as12], [ix100, ix101, ix102, ix105])
    ebgp.addPrivatePeerings(as2, [as150, as151, as152, as153, as154, as160, as161, as162, as163, as164, as170, as171], [ix100, ix101, ix102, ix105])

    # AS3 relationships
    ebgp.addPrivatePeerings(as3, [as4, as11, as12], [ix100, ix103, ix104, ix105])
    ebgp.addPrivatePeerings(as3, [as150, as151, as152, as153, as154, as160, as161, as162, as163, as164, as170, as171], [ix100, ix103, ix104, ix105])

    # AS4 relationships
    ebgp.addPrivatePeerings(as4, [as11, as12], [ix100, ix102, ix104])
    ebgp.addPrivatePeerings(as4, [as150, as151, as152, as153, as154, as160, as161, as162, as163, as164, as170, as171], [ix100, ix102, ix104])

    # AS11 relationships
    ebgp.addPrivatePeerings(as11, [as12], [ix102, ix105])
    ebgp.addPrivatePeerings(as11, [as150, as151, as152, as153, as154, as160, as161, as162, as163, as164, as170, as171], [ix102, ix105])

    # AS12 relationships
    ebgp.addPrivatePeerings(as12, [as150, as151, as152, as153, as154, as160, as161, as162, as163, as164, as170, as171], [ix101, ix104])

    ###############################################################################
    # Customize names (for visualization purpose)

    as150.getDisplayName().setDisplayName('Company A')
    as151.getDisplayName().setDisplayName('Company B')
    as152.getDisplayName().setDisplayName('Company C')
    as153.getDisplayName().setDisplayName('Company D')
    as154.getDisplayName().setDisplayName('Company E')
    as160.getDisplayName().setDisplayName('University A')
    as161.getDisplayName().setDisplayName('University B')
    as162.getDisplayName().setDisplayName('University C')
    as163.getDisplayName().setDisplayName('University D')
    as164.getDisplayName().setDisplayName('University E')
    as170.getDisplayName().setDisplayName('Government A')
    as171.getDisplayName().setDisplayName('Government B')

    ###############################################################################
    # Add layers to emulator and render

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(web)
    emu.addLayer(dns)

    emu.render()

    ###############################################################################
    # Compile with Kubernetes compiler and visualization

    # Create Kubernetes compiler with visualization enabled
    k8s = KubernetesCompiler(
        registry_prefix='localhost:5000',
        namespace='seedemu',
        use_multus=True,
        internetMapEnabled=True
    )

    # Attach the Internet Map visualization service
    k8s.attachInternetMap()

    # Compile the emulation
    emu.compile(k8s, './output_mini_internet_with_viz', override=True)

    ###############################################################################
    # Print access information

    print('='*60)
    print('Kubernetes Mini Internet with Visualization Deployment Complete!')
    print('='*60)
    print()
    print('📊 Visualization Services:')
    print('   Internet Map: http://localhost:30080')
    print('   (Access via NodePort on the Kubernetes cluster)')
    print()
    print('🚀 Deployment Information:')
    print('   Namespace: seedemu')
    print('   Output Directory: ./output_mini_internet_with_viz')
    print('   Number of ASes: 23')
    print('   Number of IXes: 6')
    print('   Services: Web + DNS + Visualization')
    print()
    print('📝 Next Steps:')
    print('   1. Build and push Docker images:')
    print('      cd output_mini_internet_with_viz && ./build_images.sh')
    print('   2. Deploy to Kubernetes:')
    print('      kubectl apply -f k8s.yaml')
    print('   3. Access visualization:')
    print('      kubectl port-forward -n seedemu service/seedemu-internet-map-service 8080:8080')
    print('      # Then open http://localhost:8080 in your browser')
    print('='*60)

if __name__ == '__main__':
    run()
