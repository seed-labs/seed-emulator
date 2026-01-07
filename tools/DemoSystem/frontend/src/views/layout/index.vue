<template>
  <el-header>
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
        <el-menu-item index="/home">首页</el-menu-item>
        <el-sub-menu index="/large-scale-internet-simulation">
          <template #title>大规模互联网仿真演示</template>
          <el-menu-item index="/large-scale-internet-simulation">大规模互联网仿真演示</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="/large-scale-blockchain-simulation">
          <template #title>大规模区块链仿真演示</template>
          <el-menu-item index="/large-scale-blockchain-simulation">大规模区块链仿真演示</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="/yesterday-reenacted">
          <template #title>昨日重现</template>
          <el-menu-item index="/yesterday-reenacted">昨日重现</el-menu-item>
          <el-menu-item index="/yesterday-reenacted/bgp">BGP 劫持攻击</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="/auto-CTF">
          <template #title>自动 CTF 靶场</template>
          <el-menu-item index="/auto-CTF">自动 CTF 靶场</el-menu-item>
        </el-sub-menu>
      </div>
    </el-menu>
  </el-header>
  <el-main>
    <router-view/>
  </el-main>
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

  .right-items {
    display: flex;
    align-items: center;
  }

  .el-menu .el-menu-item-group .el-menu-item {
    font-size: 12px;
  }
}

</style>
