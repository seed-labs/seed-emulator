<template>
  <el-config-provider :locale="lang">
  <div id="app">
    <el-row>
      <el-col :span="2">
        <img src="@/assets/seed.png">
      </el-col>
      <el-col :span="22" class="nav">
        <el-menu
            :default-active="route.path"
            class="el-menu-demo"
            mode="horizontal"
            unique-opened
            router
        >
          <el-menu-item index="/home">Home</el-menu-item>
          <el-sub-menu index="/blockchain/tx">
            <template #title>BlockChain</template>
            <el-menu-item-group title="--">
              <el-menu-item index="/blockchain/tx">Transactions</el-menu-item>
              <el-menu-item index="/blockchain/ptx">Pending Transactions</el-menu-item>
              <el-menu-item index="/blockchain/citx">Contract Internal Transactions</el-menu-item>
            </el-menu-item-group>
            <el-menu-item-group title="--">
              <el-menu-item index="/blockchain/blocks">View Blocks</el-menu-item>
            </el-menu-item-group>
            <el-menu-item-group title="--">
              <el-menu-item index="/blockchain/accounts">Accounts</el-menu-item>
              <el-menu-item index="/blockchain/wallet">Wallet</el-menu-item>
            </el-menu-item-group>
          </el-sub-menu>
        </el-menu>
      </el-col>
    </el-row>
    <el-row style="padding-top: 20px">
      <el-col :span="2"></el-col>
      <el-col :span="20">
        <router-view/>
      </el-col>
      <el-col :span="2"></el-col>
    </el-row>
  </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import {ref} from "vue";
import {useRoute} from 'vue-router';
import zhCn from 'element-plus/es/locale/lang/zh-cn'

const route = useRoute();
const lang = ref(zhCn);
</script>

<style scoped>
.el-menu .el-menu-item-group .el-menu-item {
  font-size: 12px;
}
</style>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
}
</style>