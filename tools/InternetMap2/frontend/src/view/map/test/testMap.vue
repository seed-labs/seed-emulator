<template>
  <div class="map-wrapper">
    <div ref="mapRef" class="map-layer"></div>
    <div ref="visRef" class="vis-layer"></div>
  </div>
</template>

<script setup lang="ts">
import {ref, onMounted, onBeforeUnmount, nextTick} from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

import {Network, DataSet, type Node, type Edge} from 'vis-network/standalone'

const mapRef = ref<HTMLDivElement | null>(null)
const visRef = ref<HTMLDivElement | null>(null)

let map: L.Map
let network: Network

/* ================= GEO 节点 ================= */
const GEO_NODES = [
  {id: 1, name: 'Beijing', lat: 39.9042, lon: 116.4074},
  {id: 2, name: 'Shanghai', lat: 31.2304, lon: 121.4737},
  {id: 3, name: 'Tokyo', lat: 35.6895, lon: 139.6917},
  {id: 4, name: 'London', lat: 51.5074, lon: -0.1278},
  {id: 5, name: 'Paris', lat: 48.8566, lon: 2.3522},
  {id: 6, name: 'New York', lat: 40.7128, lon: -74.006},
  {id: 7, name: 'Moscow', lat: 55.7558, lon: 37.6173},
  {id: 8, name: 'Sydney', lat: -33.8688, lon: 151.2093},
  {id: 9, name: 'Dubai', lat: 25.2048, lon: 55.2708},
  {id: 10, name: 'São Paulo', lat: -23.5505, lon: -46.6333}
]

const nodes = new DataSet<Node>()
const edges = new DataSet<Edge>()

onMounted(async () => {
  if (!mapRef.value || !visRef.value) return

  /* ---------- Leaflet ---------- */
  map = L.map(mapRef.value, {
    center: [20, 0],
    zoom: 4,
    zoomControl: false,
    worldCopyJump: false,
    maxBounds: [[-85, -180], [85, 180]],
    maxBoundsViscosity: 1
  })

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    noWrap: true,
    attribution: '© OpenStreetMap'
  }).addTo(map)

  /* ---------- vis nodes ---------- */
  GEO_NODES.forEach(n => {
    nodes.add({
      id: n.id,
      label: n.name,
      shape: 'dot',
      size: 18,
      color: '#f97316',
      fixed: true,
      physics: false
    })
  })

  for (let i = 11; i <= 40; i++) {
    nodes.add({
      id: i,
      label: `AS-${i}`,
      size: 10,
      color: '#38bdf8'
    })
    edges.add({
      from: i,
      to: ((i - 1) % 10) + 1
    })
  }

  network = new Network(
      visRef.value,
      {nodes, edges},
      {
        physics: {
          enabled: true,
          stabilization: {iterations: 150}
        },
        interaction: {
          dragView: false,
          zoomView: false
        }
      }
  )

  /* ---------- 同步经纬度 ---------- */
  const syncGeoNodes = () => {
    GEO_NODES.forEach(n => {
      const p = map.latLngToContainerPoint([n.lat, n.lon])
      nodes.update({id: n.id, x: p.x, y: p.y, fixed: true})
      if (n.id === 5) {
        console.log(`n.id: ${n.id}, P: ${p}`)
      }
    })
    network.redraw()
  }

  map.on('move zoom resize', syncGeoNodes)

  /* 关键：等待 DOM 完全布局后再修正尺寸 */
  await nextTick()
  map.invalidateSize()
  syncGeoNodes()
})

onBeforeUnmount(() => {
  map?.remove()
  network?.destroy()
})
</script>

<style scoped>
.map-wrapper {
  position: relative;
  width: 100vw;
  height: 100vh;
}

/* Leaflet 背景 */
.map-layer {
  position: absolute;
  inset: 0;
  z-index: 1;
}

/* vis overlay */
.vis-layer {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
}
</style>
