<script setup lang="ts">
import {inject, computed, reactive} from "vue";
import type {transitProvider} from "@/types/index.ts"
import type {TransitsEmulatorNodeInfo} from "@/utils/types.ts";
import {allLoading} from "@/utils/tools.ts";

const KEY = 'transitNumProvide'
const injected = inject(KEY) as transitProvider;
if (!injected) {
  throw new Error('The value provided by the parent component failed to be injected successfully');
}
const transitNum = computed({
  get: () => injected.transitNum.value,
  set: (value) => {
    injected.transitNum.value = value
  }
})
const transitNumMax = computed(() => injected.transitNumMax.value)
const onTransitNumChange = (newVal: number) => {
  injected.onTransitNumChange(newVal)
}
const transitsCheckedList = computed({
  get: () => injected.transitsCheckedList.value,
  set: (value) => {
    injected.transitsCheckedList.value = value
  }
})

const transits = computed(() => injected.transits.value)

const onTransitsCheckedChange = (value: number[]) => {
  const checkedCount = value.length
  transitsDialogState.checkbox.checkAll = checkedCount === transits.value.length
  transitsDialogState.checkbox.isIndeterminate = checkedCount > 0 && checkedCount < transits.value.length
  transitsCheckedList.value = value
}
const onTransitsCheckAllChange = (val: boolean) => {
  transitsDialogState.checkbox.isIndeterminate = false
  transitsDialogState.checkbox.checkAll = val
  transitsCheckedList.value = val ? transits.value.map((checkData: TransitsEmulatorNodeInfo) => checkData.asn) : []
}

const props = {label: 'asn', value: 'asn', disabled: 'unable'}
const transitsDialogState = reactive({
  visible: false,
  checkbox: {
    checkAll: true,
    isIndeterminate: false,
  },
  popover: {
    visible: true,
  }
})

let oldSate: {
  checkAll: boolean,
  isIndeterminate: boolean,
  transitsCheckedList: number[]
}
const onCloseTransitsDialogState = () => {
  transitsDialogState.checkbox.checkAll = oldSate.checkAll
  transitsDialogState.checkbox.isIndeterminate = oldSate.isIndeterminate
  transitsCheckedList.value = oldSate.transitsCheckedList
}

const onOpenTransitsDialogState = () => {
  oldSate = {
    checkAll: transitsDialogState.checkbox.checkAll,
    isIndeterminate: transitsDialogState.checkbox.isIndeterminate,
    transitsCheckedList: transitsCheckedList.value
  }
}

const onSubmitChange = () => {
  try {
    injected.onTransitsCheckedChange(transitsCheckedList.value)
    oldSate = {
      checkAll: transitsDialogState.checkbox.checkAll,
      isIndeterminate: transitsDialogState.checkbox.isIndeterminate,
      transitsCheckedList: transitsCheckedList.value
    }
    transitsDialogState.visible = false
  } catch (e) {
    transitsDialogState.checkbox.checkAll = oldSate.checkAll
    transitsDialogState.checkbox.isIndeterminate = oldSate.isIndeterminate
    transitsCheckedList.value = oldSate.transitsCheckedList
    const err = e instanceof Error ? e.message : e
    throw Error(err as string)
  }
}

const onSwitchChange = (val: boolean) => {
  const loading = allLoading()
  transitsDialogState.popover.visible = val
  loading.close()
}
</script>

<template>
  <el-form-item label="Num of Transit" prop="number" label-width="150px">
    <el-input-number
        v-model="transitNum"
        :step="1"
        @change="onTransitNumChange"
        :max="transitNumMax"
        :min=0
    />
  </el-form-item>
  <el-form-item label="Transits" prop="transits" label-width="150px">
    <el-tooltip content="Click to display transit details">
      <el-button type="success" @click="transitsDialogState.visible = true">Transits...</el-button>
    </el-tooltip>
  </el-form-item>
  <el-dialog
      v-model="transitsDialogState.visible"
      draggable
      :lock-scroll="false"
      title="Transit (ASN)"
      align-center
      @close="onCloseTransitsDialogState"
      @open="onOpenTransitsDialogState"
      class="transits-dialog"
  >
    <el-row>
      <el-col :span="4">
        <el-checkbox
            v-model="transitsDialogState.checkbox.checkAll"
            :indeterminate="transitsDialogState.checkbox.isIndeterminate"
            @change="onTransitsCheckAllChange"
        >
          Check all
        </el-checkbox>
      </el-col>
      <el-form-item label="Display details:" label-width="120px">
        <el-switch v-model="transitsDialogState.popover.visible" @change="onSwitchChange"/>
      </el-form-item>
    </el-row>
    <el-row>
      <el-col :span="24">
        <el-checkbox-group v-model="transitsCheckedList" :props="props" @change="onTransitsCheckedChange">
          <template v-if="transitsDialogState.popover.visible">
            <el-popover
                v-for="item in transits"
                :key="item.asn"
                placement="bottom-end"
                width="800"
                trigger="hover"
                :offset="-2"
            >
              <template #reference>
                <el-checkbox :label="item.asn">
                  AS-{{ item.asn }} ({{item.info.length}})
                </el-checkbox>
              </template>
              <el-table :data="item.info" max-height="800">
                <el-table-column label="Index" type="index" width="100" align="center"/>
                <el-table-column prop="asn" label="ASN" width="180"/>
                <el-table-column prop="name" label="Name" width="180"/>
                <el-table-column prop="role" label="Role" width="180"/>
                <el-table-column prop="nets" label="Nets">
                  <template #default="{ row }">
                    <el-space
                        v-for="net in row.nets"
                        :key="net.name"
                        direction="vertical"
                        :size="12"
                        wrap
                        :alignment="'start'"
                    >
                      <span><strong>{{ net.name }}</strong>: {{ net.address }}</span>
                    </el-space>
                  </template>
                </el-table-column>
              </el-table>
            </el-popover>
          </template>
          <template v-else>
            <el-checkbox v-for="item in transits" :key="item.asn" :label="item.asn">
              AS - {{ item.asn }}
            </el-checkbox>
          </template>
        </el-checkbox-group>
      </el-col>
    </el-row>
    <el-row :justify="'end'">
      <el-col :span="2">
        <el-button type="primary" @click="onSubmitChange" size="small">Confirm</el-button>
      </el-col>
    </el-row>
  </el-dialog>
</template>

<style scoped lang="scss">

</style>

<style lang="scss">
.transits-dialog {
  min-width: 400px;
  max-width: 800px;
  max-height: 800px;
}
</style>