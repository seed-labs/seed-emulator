<template>
  <el-breadcrumb separator="/" style="padding-bottom: 10px">
    <el-breadcrumb-item :to="{ name: 'accounts' }">
      <h1>Accounts</h1>
    </el-breadcrumb-item>
  </el-breadcrumb>
  <el-row :gutter="20" class="row">
    <el-col :span="6">
      <el-card>
        <el-statistic title="TOTAL ETH" :value="totalETH" style="margin-right: 50px"/>
      </el-card>
    </el-col>
    <el-col :span="6">
      <el-card>
        <el-statistic title="用户" :value="1128" style="margin-right: 50px"/>
      </el-card>
    </el-col>
    <el-col :span="6">
      <el-card>
        <el-statistic title="用户" :value="1128" style="margin-right: 50px"/>
      </el-card>
    </el-col>
    <el-col :span="6">
      <el-card>
        <el-statistic title="用户" :value="1128" style="margin-right: 50px"/>
      </el-card>
    </el-col>
  </el-row>
  <el-row class="row">
    <el-col :span="24">
      <el-card>
        <el-table :data="tableData" :max-height="styleExports.tHeight" v-loading="loading">
          <el-table-column prop="address" label="Account No" :show-overflow-tooltip="true" width="360"/>
          <el-table-column prop="name" label="Name"/>
          <el-table-column prop="balance" label="Balance"/>
          <el-table-column prop="change" label="Change"/>
          <el-table-column prop="nonce" label="Nonce"/>
        </el-table>
        <Pagination
            :pageParams="pageParams"
            :get-data="sliceData"
        />
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import {ref, reactive, onMounted} from 'vue';
import {AllLoading} from '@/utils/tools'
import {ElNotification} from "element-plus";
import {reqGetAccounts, reqGetTotalETH} from '@/api/index'
import Pagination from "@/components/Pagination/index.vue"
import {
  update_balance,
  get_provider,
} from "@/utils/ethersTool";
import styleExports from "@/style/blockchain/index.module.scss"

const accountsData = ref([]);
const tableData = ref([]);
const loading = ref(false);
const pageParams = reactive({
  total: 0,
  pageSize: 50,
  currentPage: 1,
  pageSizes: [2, 5, 10, 50, 100],
})
const provider = get_provider()
const totalETH = ref<string>('-1')

const getTableData = async () => {
  loading.value = true
  try {
    let accounts = await reqGetAccounts();
    if (accounts) {
      accountsData.value = accounts;
      pageParams.total = accountsData.value.length;
      sliceData()
    }
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {
    loading.value = false
  }
}

const getTotalETH = async () => {
  const allLoading = AllLoading()
  try {
    totalETH.value = await reqGetTotalETH()
    totalETH.value = `${totalETH.value} ETH`
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {
    allLoading.close()
  }
}

const getData = async () => {
  await getTotalETH()
  await getTableData()
}

const sliceData = () => {
  tableData.value = accountsData.value.slice(
      pageParams.pageSize * (pageParams.currentPage - 1),
      pageParams.pageSize * pageParams.currentPage,
  )
}

onMounted(async () => {
  await getData()
  window.setInterval(() => {
    update_balance(provider, accountsData.value)
  }, 1000)
})
</script>

<style scoped lang="scss">
.el-table {
  width: $el-table-width;
  min-height: $el-table-min-height;
  margin-bottom: $el-table-margin-bottom;
}

.row {
  padding-top: 10px
}
</style>