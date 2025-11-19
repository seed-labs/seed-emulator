<template>
  <el-breadcrumb separator="/" style="padding-bottom: 10px">
    <el-breadcrumb-item :to="{ name: 'contract internal transactions' }">
      <h1>Contract Internal Transactions</h1>
    </el-breadcrumb-item>
  </el-breadcrumb>
  <el-row class="row">
    <el-col :span="24">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>A total of 114,909 pending txns found</span>
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
        <el-table :data="tableData" :max-height="styleExports.tHeight">
          <el-table-column prop="date" label="日期" width="180"/>
          <el-table-column prop="name" label="名字" width="180"/>
          <el-table-column prop="address" label="地址"/>
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
import {reactive, ref} from "vue";
import {Search} from "@element-plus/icons-vue";
import Pagination from "@/components/Pagination/index.vue"
import styleExports from "@/style/blockchain/index.module.scss"

const pageParams = reactive({
  total: 0,
  pageSize: 50,
  currentPage: 1,
  pageSizes: [2, 5, 10, 50, 100],
})

const tableData = [
  {
    date: "2016-05-03",
    name: "Tom",
    address: "No. 189, Grove St, Los Angeles",
  },
  {
    date: "2016-05-02",
    name: "Tom",
    address: "No. 189, Grove St, Los Angeles",
  },
  {
    date: "2016-05-04",
    name: "Tom",
    address: "No. 189, Grove St, Los Angeles",
  },
  {
    date: "2016-05-01",
    name: "Tom",
    address: "No. 189, Grove St, Los Angeles",
  },
  {
    date: "2016-05-03",
    name: "Tom",
    address: "No. 189, Grove St, Los Angeles",
  },
  {
    date: "2016-05-02",
    name: "Tom",
    address: "No. 189, Grove St, Los Angeles",
  },
  {
    date: "2016-05-04",
    name: "Tom",
    address: "No. 189, Grove St, Los Angeles",
  },
  {
    date: "2016-05-01",
    name: "Tom",
    address: "No. 189, Grove St, Los Angeles",
  },
  {
    date: "2016-05-03",
    name: "Tom",
    address: "No. 189, Grove St, Los Angeles",
  },
];
const searchInput = ref('')
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
</style>

<style lang="scss">
.el-input-group__append {
  color: blue;
}
</style>