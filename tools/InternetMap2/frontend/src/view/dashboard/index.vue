<script setup lang="ts">
import {onMounted, reactive, ref, provide} from "vue";
import {Search} from "@element-plus/icons-vue";
import Pagination from "@/components/Pagination/index.vue"
import Refresh from "@/components/Refresh.vue"
import {
  reqGetContainersList,
  reqGetNetworksList,
} from "@/api/map.ts";
import {ElNotification} from "element-plus";

const pageParams1 = reactive({
  total: 0,
  pageSize: 50,
  currentPage: 1,
  pageSizes: [2, 5, 10, 50, 100],
})
const pageParams2 = reactive({
  total: 0,
  pageSize: 50,
  currentPage: 1,
  pageSizes: [2, 5, 10, 50, 100],
})
const state = reactive({
  keyword: '',
  loading: false,
  allContainerTableData: [] as any[],
  allNetTableData: [] as any[],
  containerTableData: [] as any[],
  netTableData: [] as any[],
  dialogVisible: false,
  dialogType: ref<'download' | 'add' | 'edit' | 'del' | ''>(''),
  dialogTitle: 'Tips',
})

const KEY = 'refreshProvide'
const refreshKey = ref<string>("")
const updateRefreshKey = (value: string) => {
  refreshKey.value = value
}
provide(KEY, {
      updateRefreshKey
    }
)

const onKeywordSearch = async () => {
  console.log('onKeywordSearch')
}

const onAdd = () => {
  console.log('add')
}

const onAttach = async (row) => {
  console.log("onAttach")
}

const onKill = async (row) => {
  console.log("onKill")
}

const onDownload = () => {
  console.log('download')
}
const setPageData1 = () => {
  const start = (pageParams1.currentPage - 1) * pageParams1.pageSize
  const end = pageParams1.currentPage * pageParams1.pageSize
  state.containerTableData = state.allContainerTableData.slice(start, end)
}

const setPageData2 = () => {
  const start = (pageParams2.currentPage - 1) * pageParams2.pageSize
  const end = pageParams2.currentPage * pageParams2.pageSize
  state.netTableData = state.allNetTableData.slice(start, end)
}
const getContainerTableData = async (params: {} = {}) => {
  state.loading = true
  try {
    const res = await reqGetContainersList(params)
    if (!res.ok) {
      throw Error("reqGetContainersList error")
    }
    state.allContainerTableData = res.result
    pageParams1.total = res.result.length
    setPageData1()
  } catch (e) {
    const errMsg = e instanceof Error ? e.message : String(e)
    ElNotification({
      type: 'error',
      message: errMsg
    } as any)
  } finally {
    state.loading = false
  }
}

const getNetworkTableData = async (params: {} = {}) => {
  state.loading = true
  try {
    const res = await reqGetNetworksList(params)
    if (!res.ok) {
      throw Error("reqGetNetworksList error")
    }
    state.allNetTableData = res.result
    pageParams2.total = res.result.length
    setPageData2()
  } catch (e) {
    const errMsg = e instanceof Error ? e.message : String(e)
    ElNotification({
      type: 'error',
      message: errMsg
    } as any)
  } finally {
    state.loading = false
  }
}

onMounted(() => {
  getContainerTableData()
  getNetworkTableData()
})
</script>

<template>
  <el-row justify="center">
    <el-col :span="23">
      <el-card>
        <template #header>
          <div class="card-header">
            <el-row>
              <el-col class="tools" :span="21">
                <el-button class="btn" @click="onAdd">Select all</el-button>
                <el-button class="btn" @click="onDownload">Invert selections</el-button>
                <el-button class="btn" @click="onDownload">Deselect all</el-button>
                <el-button class="btn" @click="onDownload">Attach selected</el-button>
                <el-button class="btn" @click="onDownload">Run on selected</el-button>
                <el-button class="btn" @click="onDownload">Kill selected</el-button>
                <Refresh/>
              </el-col>
              <el-col class="tools" :span="3">
                <el-input
                    v-model="state.keyword"
                    style="max-width: 240px"
                    placeholder="关键词搜索（回车）"
                    :prefix-icon="Search"
                    @keyup.enter.native="onKeywordSearch"
                />
              </el-col>
            </el-row>
          </div>
        </template>
        <el-table
            :data="state.containerTableData" style="width: 100%" table-layout="fixed"
            :header-cell-style="{fontSize: '20px', color: 'white', background: '#cfb2f6', textAlign: 'center'}"
            v-loading="state.loading"
            element-loading-text="数据加载中..."
            highlight-current-row
            max-height="400"
            :cell-style="{textAlign: 'center'}"
        >
          <el-table-column type="selection" width="55"/>
          <el-table-column label="Index" type="index" width="100" align="center"/>
          <el-table-column prop="asn" label="ASN">
            <template #="{row}">
              {{ row.meta.emulatorInfo.asn }}
            </template>
          </el-table-column>
          <el-table-column prop="name" label="Name">
            <template #="{row}">
              {{ row.meta.emulatorInfo.name }}
            </template>
          </el-table-column>
          <el-table-column prop="type" label="Type">
            <template #="{row}">
              {{ row.meta.emulatorInfo.role }}
            </template>
          </el-table-column>
          <el-table-column prop="ip" label="IP Address(es)">
            <template #="{row}">
              <el-row v-for="net in row.meta.emulatorInfo.nets" justify="center">
                <strong>{{ net.name }}</strong>: <span>{{ net.address }}</span>
              </el-row>
            </template>
          </el-table-column>
          <el-table-column label="Action">
            <template #="{row}">
              <el-button class="btn" type="primary" size="small" @click="onAttach(row)">Attach</el-button>
              <el-button class="btn" type="danger" size="small" @click="onKill(row)">Kill</el-button>
            </template>
          </el-table-column>
        </el-table>
        <Pagination
            :pageParams="pageParams1"
            :get-data="setPageData1"
        />
      </el-card>
      <el-divider/>
      <el-card>
        <template #header>
          <div class="card-header">
            <el-row>
              <el-col class="tools" :span="21">
                <el-button class="btn" @click="onAdd">Select all</el-button>
                <el-button class="btn" @click="onDownload">Invert selections</el-button>
                <el-button class="btn" @click="onDownload">Deselect all</el-button>
                <el-button class="btn" @click="onDownload">Attach selected</el-button>
                <el-button class="btn" @click="onDownload">Run on selected</el-button>
                <el-button class="btn" @click="onDownload">Kill selected</el-button>
                <Refresh/>
              </el-col>
              <el-col class="tools" :span="3">
                <el-input
                    v-model="state.keyword"
                    style="max-width: 240px"
                    placeholder="关键词搜索（回车）"
                    :prefix-icon="Search"
                    @keyup.enter.native="onKeywordSearch"
                />
              </el-col>
            </el-row>
          </div>
        </template>
        <el-table
            :data="state.netTableData" style="width: 100%" table-layout="fixed"
            :header-cell-style="{fontSize: '20px', color: 'white', background: '#cfb2f6', textAlign: 'center'}"
            v-loading="state.loading"
            element-loading-text="数据加载中..."
            highlight-current-row
            max-height="400"
            :cell-style="{textAlign: 'center'}"
        >
          <el-table-column type="selection" width="55"/>
          <el-table-column label="Index" type="index" width="100" align="center"/>
          <el-table-column prop="asn" label="ASN(scope)">
            <template #="{row}">
              {{ row.meta.emulatorInfo.scope }}
            </template>
          </el-table-column>
          <el-table-column prop="name" label="Name">
            <template #="{row}">
              {{ row.meta.emulatorInfo.name }}
            </template>
          </el-table-column>
          <el-table-column prop="type" label="Type">
            <template #="{row}">
              {{ row.meta.emulatorInfo.type }}
            </template>
          </el-table-column>
          <el-table-column prop="prefix" label="Network Prefix">
            <template #="{row}">
              {{ row.meta.emulatorInfo.prefix }}
            </template>
          </el-table-column>
        </el-table>
        <Pagination
            :pageParams="pageParams2"
            :get-data="setPageData2"
        />
      </el-card>
    </el-col>
  </el-row>
</template>

<style scoped lang="scss">
.tools {
  display: flex;
  gap: 0.2%;
  justify-items: center;

  .btn {
    color: #cfb2f6;
  }

  :deep(.el-button+.el-button) {
    margin-left: 0;
  }
}

.el-table {
  width: 100%;;
  min-height: 300px;
  margin-bottom: 20px;
}

</style>