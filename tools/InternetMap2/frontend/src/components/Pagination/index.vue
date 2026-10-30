<template>
  <el-pagination
      ref="paginationRef"
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
import {toRefs, ref, nextTick, watch} from "vue";

interface Props {
  pageParams?: {
    total: number
    pageSize: number
    currentPage: number
    pageSizes: number[]
  },
  getData: () => void
}

const props = withDefaults(defineProps<Props>(), {
  pageParams: () => ({
    total: 0,
    pageSize: 20,
    currentPage: 1,
    pageSizes: [2, 5, 10, 50, 100],
  })
})
const disabled = ref(false)
const paginationRef = ref()

const {pageParams, getData} = toRefs(props)
const onSizeChange = async (val: number) => {
  pageParams.value.pageSize = val
  getData.value()
}
const onCurrentChange = async (val: number) => {
  pageParams.value.currentPage = val
  getData.value()
}

watch(disabled,
    async (newVal: boolean) => {
      if (!newVal) {
        await nextTick()
        const jumpInput = paginationRef.value?.$el?.querySelector('.el-pagination__jump')
        if (jumpInput) {
          jumpInput.removeAttribute('disabled')
        }
      }
    },
    {immediate: true}
)
</script>

<style scoped>

</style>