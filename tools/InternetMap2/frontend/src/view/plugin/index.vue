<script setup lang="ts">
import {onMounted, reactive, ref, provide} from "vue";
import {Search} from "@element-plus/icons-vue";
import Pagination from "@/components/Pagination/index.vue"
import Refresh from "@/components/Refresh.vue"
import {
  reqGetInstallList,
  reqInstall,
  reqUninstall,
  type pluginType
} from "@/api/plugin.ts";
import {ElNotification} from "element-plus";
import {allLoading} from "@/utils/tools.ts";

const pageParams = reactive({
  total: 0,
  pageSize: 50,
  currentPage: 1,
  pageSizes: [2, 5, 10, 50, 100],
})
const state = reactive({
  keyword: '',
  loading: false,
  tableData: [] as any[],
  dialogVisible: false,
  dialogType: ref<'download' | 'add' | 'edit' | 'del' | ''>(''),
  dialogTitle: 'Tips',
})

const onKeywordSearch = async () => {
  await getTableData({
    keyword: state.keyword
  })
}

const onAdd = () => {
  console.log('add')
}

const onInstall = async (row: pluginType) => {
  console.log(row)
  const loading = allLoading()
  try {
    const res = await reqInstall({id: row.id, title: row.name})
    if (!res.ok) {
      throw Error(res.message)
    }
  } catch (e) {
    const errMsg = e instanceof Error ? e.message : String(e)
    ElNotification({
      type: 'error',
      message: errMsg
    } as any)
  } finally {
    loading.close()
  }
}

const onUninstall = async (row: pluginType) => {
  const loading = allLoading()
  try {
    const res = await reqUninstall({id: row.id, title: row.name})
    if (!res.ok) {
      throw Error("reqUninstall error")
    }
  } catch (e) {
    const errMsg = e instanceof Error ? e.message : String(e)
    ElNotification({
      type: 'error',
      message: errMsg
    } as any)
  } finally {
    loading.close()
  }
}

const onDownload = () => {
  console.log('download')
}

const KEY = 'refreshProvide'
const refreshKey = ref<string>("")
const updateRefreshKey = (value: string) => {
  refreshKey.value = value
}
provide(KEY, {
      updateRefreshKey
    }
)
const getTableData = async (params: {} = {}) => {
  state.loading = true
  try {
    const res = await reqGetInstallList(params)
    if (!res.ok) {
      throw Error("reqGetInstallList error")
    }
    const start = (pageParams.currentPage - 1) * pageParams.pageSize
    const end = pageParams.currentPage * pageParams.pageSize
    state.tableData = res.result.slice(start, end)
    pageParams.total = res.result.length
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
  getTableData()
})
</script>

<template>
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
                placeholder="Keyword search (Press Enter)"
                :prefix-icon="Search"
                @keyup.enter.native="onKeywordSearch"
            />
          </el-col>
        </el-row>
      </div>
    </template>
    <el-table
        :data="state.tableData" style="width: 100%" table-layout="fixed"
        :header-cell-style="{fontSize: '20px', color: 'white', background: '#cfb2f6', textAlign: 'center'}"
        v-loading="state.loading"
        element-loading-text="loading..."
        highlight-current-row
        max-height="800"
        :cell-style="{textAlign: 'center'}"
    >
      <el-table-column type="selection" width="55"/>
      <el-table-column label="Index" type="index" width="100" align="center"/>
      <el-table-column prop="name" label="Name"/>
      <el-table-column label="Action">
        <template #default="{row}">
          <el-button class="btn" type="primary" size="small" @click="onInstall(row)">Install</el-button>
          <el-button class="btn" type="danger" size="small" @click="onUninstall(row)">Uninstall</el-button>
        </template>
      </el-table-column>
    </el-table>
    <Pagination
        :pageParams="pageParams"
        :get-data="getTableData"
    />
  </el-card>
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
  min-height: 400px;
  margin-bottom: 20px;
}

</style>