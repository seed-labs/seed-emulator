<template>
  <el-row>
    <el-col :span="24">
      <el-menu
          :default-active="route.path"
          class="menu"
          mode="horizontal"
          unique-opened
          router
      >
        <el-menu-item index="0" class="logo-item">
          <img
              style="height: 80%;"
              src="@/assets/img/seed.png"
              alt="logo"
          />
        </el-menu-item>
        <div class="right-items">
          <el-menu-item index="/home">Home</el-menu-item>
          <el-menu-item index="/dashboard">Dashboard</el-menu-item>
          <el-menu-item index="/plugin">Plugin</el-menu-item>
          <el-sub-menu index="/map">
            <template #title>Map</template>
<!--            <el-menu-item index="/ixMap">IXMap</el-menu-item>-->
            <el-menu-item index="/transitMap">TransitMap</el-menu-item>
            <el-menu-item index="/map">Map</el-menu-item>
          </el-sub-menu>
        </div>
      </el-menu>
    </el-col>
  </el-row>
  <el-row style="padding-top: 20px">
    <el-col :span="24">
      <router-view/>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import {useRoute} from 'vue-router';

const route = useRoute();
</script>

<style scoped lang="scss">
.menu {
  display: flex;
  align-items: center;
  justify-content: space-between;

  /* 右侧菜单项容器保持水平排列 */
  .right-items {
    display: flex;
    align-items: center;
  }

  .el-menu .el-menu-item-group .el-menu-item {
    font-size: 12px;
  }
}

</style>
