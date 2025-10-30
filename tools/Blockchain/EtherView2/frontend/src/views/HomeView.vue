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
  <el-row :gutter="20" style="padding: 20px 0">
    <el-col>
      <ul style="display: grid;grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    list-style: none;
    padding: 0;
    margin: 0;">
        <li v-for="(value, key, i) in statisticInfo">
          <el-card>
            <el-statistic :title="value.title" :value="value.value">
              <template #prefix>
                <el-icon>
                  <component :is="value.icon"></component>
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
            <span>Latest Blocks</span>
            <el-button class="button" type="text">Customize</el-button>
          </div>
        </template>
        <el-table :data="currentBlocksData" v-loading="tableLoading">
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
        <el-table :data="currentTxData" v-loading="tableLoading">
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

<script lang="ts">
import {Basketball, CreditCard, Money, Position, TakeawayBox, Timer, User} from "@element-plus/icons-vue";

export default {
  components: {
    Position,
    User,
    CreditCard,
    Money,
    Basketball,
    Timer,
    TakeawayBox,
  }
}
</script>

<script setup lang="ts">
import Decimal from 'decimal.js';
import {ref, onMounted, reactive} from 'vue'
import {useRouter} from 'vue-router'
import {ElNotification} from "element-plus";
import {Search, Back} from '@element-plus/icons-vue'
import {reqGetEtherScan, reqGetTXs, reqGetTotalETH} from '@/api/index'
import {AllLoading} from '@/utils/tools'
import {
  get_provider,
  get_blocks_with_transactions,
  get_blocks_total,
  get_GAS_price,
  calcMarketCap
} from "@/utils/ethersTool";

const router = useRouter()
const input3 = ref('')
const select = ref('')
const tableLoading = ref(false);
const currentBlocksData = ref([]);
const currentTxData = ref([]);
const number = 20
const blocksTotal = ref(0);
const provider = get_provider()
const totalETH = ref<Decimal>()
const statisticInfo = reactive({
  etherPrice: {
    title: 'ETH PRICE',
    value: '',
    icon: 'Position'
  },
  TXN: {
    title: 'TRANSACTIONS',
    value: '',
    icon: 'CreditCard'
  },
  gasPrice: {
    title: 'GAS PRICE',
    value: "",
    icon: 'Money'
  },
  marketCap: {
    title: 'MARKET CAP',
    value: "",
    icon: 'Basketball'
  },
  lastFinalizedBlock: {
    title: 'LAST FINALIZED BLOCK',
    value: '',
    icon: 'Timer'
  },
  lastSafeBlock: {
    title: 'LAST SAFE BLOCK',
    value: '',
    icon: 'TakeawayBox'
  },
})
const getTableData = async () => {
  tableLoading.value = true
  try {
    blocksTotal.value = await get_blocks_total(provider)
    const start = blocksTotal.value - number + 1 > 0 ? blocksTotal.value - number + 1 : 0
    const {blocks, transactions} = await get_blocks_with_transactions(provider, start, blocksTotal.value, 20);
    statisticInfo.lastFinalizedBlock.value = blocksTotal.value.toString()
    statisticInfo.lastSafeBlock.value = blocksTotal.value.toString()
    if (blocks) {
      currentBlocksData.value = blocks;
      currentTxData.value = transactions;
    }
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {
    tableLoading.value = false
  }
}

const getEtherScanData = async () => {
  const allLoading = AllLoading()
  try {
    const ret = await reqGetEtherScan()
    const gasPrice = await get_GAS_price(provider)
    const ret2 = await reqGetTXs()
    if (ret.status && ret2.status) {
      statisticInfo.etherPrice.value = ret.data.etherPrice
      statisticInfo.gasPrice.value = gasPrice
      statisticInfo.marketCap.value = calcMarketCap(ret.data.etherPrice, totalETH.value)
      statisticInfo.TXN.value = ret2.data.total;
    } else {
      ElNotification({
        type: 'error',
        message: ret.message
      } as any)
    }
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {
    allLoading.close()
  }
}

const getTotalETH = async () => {
  try {
    const totalETHStr = await reqGetTotalETH()
    totalETH.value = new Decimal(totalETHStr)
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  }
}

const getData = async () => {
  await getTotalETH()
  await getEtherScanData()
  await getTableData()
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