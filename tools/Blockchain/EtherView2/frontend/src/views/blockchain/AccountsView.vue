<template>
  <el-breadcrumb separator="/" style="padding-bottom: 10px">
    <el-breadcrumb-item :to="{ name: 'accounts' }">
      <h1>Accounts</h1>
    </el-breadcrumb-item>
  </el-breadcrumb>
  <el-row :gutter="20" class="row">
    <el-col :span="6">
      <el-card>
        <el-statistic title="用户" :value="1128" style="margin-right: 50px">
          <template #suffix>
            <el-icon>
              <User/>
            </el-icon>
          </template>
        </el-statistic>
      </el-card>
    </el-col>
    <el-col :span="6">
      <el-card>
        <el-statistic title="用户" :value="1128" style="margin-right: 50px">
          <template #suffix>
            <el-icon>
              <User/>
            </el-icon>
          </template>
        </el-statistic>
      </el-card>
    </el-col>
    <el-col :span="6">
      <el-card>
        <el-statistic title="用户" :value="1128" style="margin-right: 50px">
          <template #suffix>
            <el-icon>
              <User/>
            </el-icon>
          </template>
        </el-statistic>
      </el-card>
    </el-col>
    <el-col :span="6">
      <el-card>
        <el-statistic title="用户" :value="1128" style="margin-right: 50px">
          <template #suffix>
            <el-icon>
              <User/>
            </el-icon>
          </template>
        </el-statistic>
      </el-card>
    </el-col>
  </el-row>
  <el-row class="row">
    <el-col :span="24">
      <el-card>
        <el-table :data="tableData" max-height="500" v-loading="loading">
          <el-table-column prop="address" label="Account No" :show-overflow-tooltip="true" width="360"/>
          <el-table-column prop="name" label="Name"/>
          <el-table-column prop="balance" label="Balance"/>
          <el-table-column prop="change" label="Change"/>
          <el-table-column prop="nonce" label="Nonce"/>
        </el-table>
        <Pagination
            :pageParams="pageParams"
            :slice-data="sliceData"
        />
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import {ref, reactive, onMounted} from 'vue';
import {User} from "@element-plus/icons-vue";
import {ElNotification} from "element-plus";
import {reqGetAccounts} from '@/api/index'
import Pagination from "@/components/Pagination/index.vue"
import {
  get_balance,
  get_nonce, get_provider,
} from "@/utils/ethersTool";

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

const getData = async () => {
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

const sliceData = () => {
  tableData.value = accountsData.value.slice(
      pageParams.pageSize * (pageParams.currentPage - 1),
      pageParams.pageSize * pageParams.currentPage,
  )
}

const update_balance = async () => {
  // sort the data by address
  let data = accountsData.value;

  if (data === null) return;

  for (let r of data) {
    let balance = await get_balance(provider, r.address);
    let nonce = await get_nonce(provider, r.address);
    let change = 0;

    if ("balance" in r) {
      change = balance - r["balance"];
      if (change == 0) {
        // If change == 0, keep the previous change
        change = r["recent-change"];
      } else r["recent-change"] = change;

      r["balance"] = balance;
    } else {
      r["balance"] = balance;
      r["recent-change"] = 0;
    }

    r.balance = balance
    r.change = change
    r.nonce = nonce
  }
}

onMounted(async () => {
  await getData()
  window.setInterval(() => {
    update_balance()
  }, 1000)
})
</script>

<style scoped lang="scss">
.el-table {
  width: 100%;
  // min-height: 400px;
  margin-bottom: 20px;
}

.row {
  padding-top: 10px
}
</style>