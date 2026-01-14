<script setup lang="ts">
import mapImg from '@/assets/img/map.png'
import transitMapImg from '@/assets/img/transitMap.png'
import dashboardImg from '@/assets/img/dashboard.png'
import pluginImg from '@/assets/img/plugin.png'

</script>

<template>
  <el-row>
    <el-col>
      <section class="jumbotron text-center">
        <div class="container">
          <h1>INTERNET MAP</h1>
          <p class="lead text-muted">This is a work-in-progress prototype of the internet-map..</p>
        </div>
      </section>
    </el-col>
  </el-row>
  <el-row style="padding: 20px 0" :justify="'center'">
    <el-col :span="22">
      <ul style="
        display: grid;grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        list-style: none;
        padding: 0;
        margin: 0;"
      >
        <li>
          <router-link
              :to="{ name: 'map'}"
          >
            <el-tooltip
                class="box-item"
                effect="dark"
                content="The network topology diagram displays interconnection relationships between nodes and networks, along with auxiliary functions including filtering, search, settings, replay, and logging."
                placement="bottom-start"
            >
              <el-card>
                <template #header>
                  <h3>MAP</h3>
                </template>
                <el-image :src="mapImg" :fit="'fit'"/>
              </el-card>
            </el-tooltip>
          </router-link>
        </li>
        <li>
          <router-link
              :to="{ name: 'transitMap'}"
          >
            <el-tooltip
                class="box-item"
                effect="dark"
                content="Similar to the map page in function, the difference lies in the display dimension. transitMap only shows up to the transit dimension and does not display the Host at a deeper level."
                placement="bottom-start"
            >
              <el-card>
                <template #header>
                  <h3>TRANSIT MAP</h3>
                </template>
                <el-image :src="transitMapImg" :fit="'fit'"/>
              </el-card>
            </el-tooltip>
          </router-link>
        </li>
        <li>
          <router-link
              :to="{ name: 'dashboard'}"
          >
            <el-tooltip
                class="box-item"
                effect="dark"
                content="seedemu dashboard, displays current emulator nodes and networks."
                placement="bottom"
            >
              <el-card>
                <template #header>
                  <h3>DASHBOARD</h3>
                </template>
                <el-image :src="dashboardImg" :fit="'fit'"/>
              </el-card>
            </el-tooltip>
          </router-link>
        </li>
        <li>
          <router-link
              :to="{ name: 'plugin'}"
          >
            <el-tooltip
                class="box-item"
                effect="dark"
                content="Plugin installation page."
                placement="bottom"
            >
              <el-card>
                <template #header>
                  <h3>PLUGIN</h3>
                </template>
                <el-image :src="pluginImg" :fit="'fit'"/>
              </el-card>
            </el-tooltip>
          </router-link>
        </li>
      </ul>
    </el-col>
  </el-row>
</template>

<style scoped lang="scss">
.jumbotron {
  padding: 2rem 1rem;
  margin-bottom: 2rem;
  background-color: #e9ecef;
  border-radius: .3rem;
}

@media (min-width: 576px) {
  .jumbotron {
    padding: 4rem 2rem;
  }
}

.container {
  text-align: center;
}
</style>