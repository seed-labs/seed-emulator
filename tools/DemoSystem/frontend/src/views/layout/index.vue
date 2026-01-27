<template>
  <el-container style="height: 100vh;">
    <el-header>
      <Menu
          :menuList="menus"
      />
    </el-header>
    <el-main>
      <router-view/>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import Menu from '@/views/layout/Menu/index.vue'
import {menus} from "@/extensions/index.ts"

</script>

<style scoped lang="scss">

</style>

