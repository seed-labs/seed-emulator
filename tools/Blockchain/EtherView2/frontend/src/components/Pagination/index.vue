<template>
  <el-pagination
      v-model:current-page="pageParams.currentPage"
      v-model:page-size="pageParams.pageSize"
      :page-sizes="pageParams.pageSizes"
      background
      layout="total, sizes, prev, pager, next, ->, jumper"
      :total="pageParams.total"
      @size-change="onSizeChange"
      @current-change="onCurrentChange"
      :disabled="disabled"
  />
</template>

<script lang="ts" setup>
// 接受父组件传参
// const {
//   pageParams = {
//     total: 0,
//     pageSize: 5,
//     currentPage: 1,
//     pageSizes: [2, 5, 10, 50, 100],
//   },
//   sliceData
// } = defineProps<{
//   pageParams: {
//     total: number,
//     pageSize: number,
//     currentPage: number,
//     pageSizes: Array<number>,
//   },
//   sliceData: () => void,
// }>()
// const onSizeChange = async (val: number) => {
//   pageParams.pageSize = val
//   sliceData()
// }
// const onCurrentChange = async (val: number) => {
//   pageParams.currentPage = val
//   sliceData()
// }

import {toRefs} from "vue";

const props = defineProps({
  pageParams: {
    type: {
      total: Number,
      pageSize: Number,
      currentPage: Number,
      pageSizes: Array<Number>,
    },
    default: () => ({
      total: 0,
      pageSize: 20,
      currentPage: 1,
      pageSizes: [2, 5, 10, 50, 100],
    })
  },
  getData: {
    type: Function,
    default: () => () => {
    },
  },
})

const {pageParams, getData} = toRefs(props)
const onSizeChange = async (val: Number) => {
  pageParams.value.pageSize = val
  getData.value()
}
const onCurrentChange = async (val: Number) => {
  pageParams.value.currentPage = val
  getData.value()
}
</script>

<style scoped>

</style>