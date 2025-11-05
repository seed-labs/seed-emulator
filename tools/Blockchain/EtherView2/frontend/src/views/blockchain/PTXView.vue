<template>
  <el-breadcrumb separator="/" style="padding-bottom: 10px">
    <el-breadcrumb-item :to="{ name: 'pending transactions' }">
      <h1>Pending Transactions</h1>
    </el-breadcrumb-item>
  </el-breadcrumb>
  <el-row class="row">
    <el-col :span="24">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>A total of
              <span style="color: #0a53be; font-size: 1.5em">{{ pageParams.total }}</span>
               pending txns found</span>
            <el-popover
                placement="bottom-start"
                :width="300"
                trigger="click"
            >
              <template #reference>
                <el-button color="#a9a9b1" size="small" :icon="Search" class="button"></el-button>
              </template>
              <el-input v-model="searchInput" placeholder="请输入" class="input-with-select">
                <template #append>
                  <el-button size="small" class="button" color="#191983">Find</el-button>
                </template>
              </el-input>
            </el-popover>
          </div>
        </template>
        <el-table :data="tableData" :max-height="styleExports.tHeight" v-loading="loading">
          <el-table-column prop="hash" label="Hash" width="360" :show-overflow-tooltip="true">
            <template #default="scope">
              <router-link
                  :to="{ name: 'txInfo', params: { id: scope.row.hash } }"
                  class="el-link el-link--primary">
                {{ scope.row.hash }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column prop="time" label="Age" width="120"/>
          <el-table-column prop="nonce" label="Nonce" width="240" :show-overflow-tooltip="true"/>
          <el-table-column prop="gasPrice" label="Gas Price" width="240" :show-overflow-tooltip="true"/>
          <el-table-column prop="from" label="From" width="360" :show-overflow-tooltip="true"/>
          <el-table-column prop="to" label="To" width="360" :show-overflow-tooltip="true"/>
          <el-table-column prop="value" label="Amount"/>
        </el-table>
        <Pagination
            :pageParams="pageParams"
            :get-data="getData"
        />
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import {ElNotification} from "element-plus";
import {ref, reactive, onMounted} from "vue";
import {Search} from "@element-plus/icons-vue";
import Pagination from "@/components/Pagination/index.vue"
import {
  get_provider,
  getPendingTxs,
} from "@/utils/ethersTool";
import styleExports from "@/style/blockchain/index.module.scss"

const loading = ref(false);
const tableData = ref([]);
const pTransactionsData = ref([]);
const searchInput = ref('')
const pageParams = reactive({
  total: 0,
  pageSize: 50,
  currentPage: 1,
  pageSizes: [2, 5, 10, 50, 100],
})
const provider = get_provider()


const getData = async () => {
  loading.value = true
  try {
    pTransactionsData.value = await getPendingTxs(provider);
    pageParams.total = pTransactionsData.value.length;
    sliceData()
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {
    console.log('pTransactionsData: ', pTransactionsData)
    loading.value = false
  }
}

const sliceData = () => {
  tableData.value = pTransactionsData.value.slice(
      pageParams.pageSize * (pageParams.currentPage - 1),
      pageParams.pageSize * pageParams.currentPage,
  )
}

onMounted(async () => {
  await getData()
})
</script>

<style scoped lang="scss">
.el-table {
  width: $el-table-width;
  min-height: $el-table-min-height;
  margin-bottom: $el-table-margin-bottom;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.row {
  padding-top: 10px
}

.el-input-group__append {
  color: blue;
}
</style>