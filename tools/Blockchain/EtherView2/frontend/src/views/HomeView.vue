<template>
  <el-row style="padding: 20px 0">
    <el-col :span="12">
      <div class="mt-4">
        <el-input v-model="input3" placeholder="请输入" class="input-with-select">
          <template #prepend>
            <el-select v-model="select" placeholder="Select" style="width: 115px">
              <el-option label="Restaurant" value="1"/>
              <el-option label="Order No." value="2"/>
              <el-option label="Tel" value="3"/>
            </el-select>
          </template>
          <template #append>
            <el-button :icon="Search"/>
          </template>
        </el-input>
      </div>
    </el-col>
  </el-row>
  <el-row style="padding: 20px 0">
    <el-col>
      <ul style="display: grid;grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    list-style: none;
    padding: 0;
    margin: 0;">
        <li>
          <el-card>
            <el-statistic title="用户" :value="1128" style="margin-right: 50px">
              <template #suffix>
                <el-icon>
                  <User/>
                </el-icon>
              </template>
            </el-statistic>
          </el-card>
        </li>
        <li>
          <el-card>
            <el-statistic title="用户" :value="1128" style="margin-right: 50px">
              <template #suffix>
                <el-icon>
                  <User/>
                </el-icon>
              </template>
            </el-statistic>
          </el-card>
        </li>
        <li>
          <el-card>
            <el-statistic title="用户" :value="1128" style="margin-right: 50px">
              <template #suffix>
                <el-icon>
                  <User/>
                </el-icon>
              </template>
            </el-statistic>
          </el-card>
        </li>
        <li>
          <el-card>
            <el-statistic title="用户" :value="1128" style="margin-right: 50px">
              <template #suffix>
                <el-icon>
                  <User/>
                </el-icon>
              </template>
            </el-statistic>
          </el-card>
        </li>
        <li>
          <el-card>
            <el-statistic title="用户" :value="1128" style="margin-right: 50px">
              <template #suffix>
                <el-icon>
                  <User/>
                </el-icon>
              </template>
            </el-statistic>
          </el-card>
        </li>
        <li>
          <el-card>
            <el-statistic title="用户" :value="1128" style="margin-right: 50px">
              <template #suffix>
                <el-icon>
                  <User/>
                </el-icon>
              </template>
            </el-statistic>
          </el-card>
        </li>
      </ul>
    </el-col>
  </el-row>
  <el-row :gutter="20">
    <el-col :span="12">
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span>Latest Blcoks</span>
            <el-button class="button" type="text">Customize</el-button>
          </div>
        </template>
        <el-table :data="currentBlocksData" v-loading="loading">
          <el-table-column prop="number" label="Number" width="240"/>
          <el-table-column prop="txn" label="TxN" width="240"/>
          <el-table-column prop="reward" label="Reward"/>
        </el-table>
        <template #footer>
          <el-button type="primary" :icon="Back" @click="handleClickBlock">view all</el-button>
        </template>
      </el-card>
    </el-col>
    <el-col :span="12">
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span>Latest Transactions</span>
            <el-button class="button" type="text">Customize</el-button>
          </div>
        </template>
        <el-table :data="currentTxData" v-loading="loading2">
          <el-table-column prop="blockNumber" label="BlockNumber" width="120" :show-overflow-tooltip="true"/>
          <el-table-column prop="hash" label="Hash" width="200" :show-overflow-tooltip="true"/>
          <el-table-column prop="from" label="From" width="200" :show-overflow-tooltip="true"/>
          <el-table-column prop="to" label="To" width="200" :show-overflow-tooltip="true"/>
          <el-table-column prop="eth" label="Amount"/>
        </el-table>
        <template #footer>
          <el-button type="primary" :icon="Back" @click="handleClickTX">view all</el-button>
        </template>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import {ref, onMounted} from 'vue'
import {useRouter} from 'vue-router'
import {ElNotification} from "element-plus";
import {Search, User, Back} from '@element-plus/icons-vue'
import {
  get_provider,
  get_blocks,
  get_blocks_total,
  show_current_transactions
} from "@/utils/ethersTool";

const router = useRouter()
const input3 = ref('')
const select = ref('')
const loading = ref(false);
const loading2 = ref(false);
const currentBlocksData = ref([]);
const currentTxData = ref([]);
const number = 20
const provider = get_provider()
const getData = async () => {
  loading.value = loading2.value = true
  try {
    let total = await get_blocks_total(provider)
    let start = total - number + 1 > 0 ? total - number + 1 : 0
    let {blocks} = await get_blocks(provider, start, total);
    if (blocks) {
      currentBlocksData.value = blocks;
      loading.value = false
      currentTxData.value = await show_current_transactions(provider, number);
      loading2.value = false
    }
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {
    loading.value = loading2.value = false
  }
}

const handleClickBlock = () => {
  router.push({name: 'blocks'})
}

const handleClickTX = () => {
  router.push({name: 'transactions'})
}

onMounted(async () => {
  await getData()
})
</script>

<style lang="scss" scoped>
@use '@/style/home.module.scss' as style;

.el-table {
  height: style.$t-height
}
</style>

<style lang="scss">
.input-with-select .el-input-group__prepend {
  background-color: var(--el-fill-color-blank);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>