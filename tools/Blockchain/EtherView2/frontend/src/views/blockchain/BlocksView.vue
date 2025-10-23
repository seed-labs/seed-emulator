<template>
  <el-breadcrumb separator="/" style="padding-bottom: 10px">
    <el-breadcrumb-item :to="{ name: 'blocks' }">
      <h1>Blocks</h1>
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
        <el-table :data="blocksData" v-loading="loading" max-height="500">
          <el-table-column prop="number" label="Number" width="240"/>
          <el-table-column prop="timestamp" label="Age" width="120">
            <template #default="scope">{{ timeTo(scope.row.timestamp) }}</template>
          </el-table-column>
          <el-table-column prop="txn" label="TxN" width="240"/>
          <el-table-column prop="reward" label="Reward"/>
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
import {ref, reactive, onMounted} from 'vue';
import {User} from "@element-plus/icons-vue";
import {ElNotification} from "element-plus";
import Pagination from "@/components/Pagination/index.vue"

import {
  timeTo,
  get_provider,
  get_blocks,
  get_blocks_total,
} from "@/utils/ethersTool";

const blocksData = ref([]);
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
    pageParams.total = await get_blocks_total(provider)
    let {blocks} = await get_blocks(
        provider,
        pageParams.pageSize * (pageParams.currentPage - 1),
        pageParams.pageSize * pageParams.currentPage - 1,
        true
    );
    if (blocks) {
      blocksData.value = blocks;
      blocksData.value.sort((a, b) => b.timestamp - a.timestamp)
    }
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {
    loading.value = false
    console.log('blocksData: ', blocksData)
  }
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

.row {
  padding-top: 10px
}
</style>