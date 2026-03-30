<script setup lang="ts" xmlns="http://www.w3.org/1999/html">

import {ref, reactive, onMounted} from "vue";
import {ElNotification, type FormInstance, type FormRules} from 'element-plus'
import {useGlobalStore} from "@/store"
import {reqRestoreAccounts, reqSendTX} from '@/api/index'
import styleExports from "@/style/blockchain/index.module.scss"
import {get_provider, update_balance} from "@/utils/ethersTool.ts";

const globalStore = useGlobalStore()
const provider = get_provider()
const alertDesc = 'The following data are all experimental data. Please do not apply them in actual scenarios !!!'
const state = reactive({
  loading: false,
  tableData: globalStore.restoreAccountsList as any[],
  senderKeyDisabled: true,
  dialogVisible: false,
  dialogType: ref<'download' | 'add' | 'edit' | 'del' | ''>(''),
  dialogTitle: 'Send Transaction',
})

interface SendTXRuleFormType {
  sender: string
  receiver: string
  amount: number
  senderKey: string
  nonce: number
}

const sendTXFormRef = ref<FormInstance>()
const sendTXRulesForm = reactive<SendTXRuleFormType>({
  sender: '',
  receiver: '',
  senderKey: '',
  amount: 0,
  nonce: 0,
})
const sendTXRules = reactive<FormRules<SendTXRuleFormType>>({
  sender: [
    {required: true, message: 'Please input sender address', trigger: 'change'},
  ],
  receiver: [
    {required: true, message: 'Please input receiver address', trigger: 'change'},
  ],
  amount: [
    {required: true, message: 'Please input transaction amount', trigger: 'change'},
  ],
  senderKey: [
    {required: true, message: 'Please input senderKey', trigger: 'change'},
  ],
})

const onSubmitSendTXForm = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  await formEl.validate(async (valid, fields) => {
    if (valid) {
      try {
        const res = await reqSendTX(sendTXRulesForm)
        if (res.status) {
          state.dialogVisible = false
          ElNotification({
            type: 'success',
            message: 'Transaction success'
          } as any)
        } else {
          throw Error(res.message)
        }
      } catch (e) {
        ElNotification({
          type: 'error',
          message: e
        } as any)
      }
    } else {
      ElNotification({
        type: 'error',
        message: fields
      } as any)
    }
  })
}

const resetForm = (formEl: FormInstance | undefined) => {
  state.dialogVisible = false
  if (!formEl) return
  formEl.resetFields()
}

interface restoreAccountsRuleFormType {
  mnemonic: string
  accountNum: number
}

const restoreAccountsFormRef = ref<FormInstance>()
const restoreAccountsFormInline = reactive<restoreAccountsRuleFormType>({
  mnemonic: '',
  accountNum: 5,
})
const validateMnemonic = (rule: any, value: any, callback: any) => {
  if (value.split(' ').length !== 12) {
    callback(new Error('Please input 12 mnemonic phrases, separated by Spaces'))
  } else {
    callback()
  }
}
const restoreAccountsRules = reactive<FormRules<restoreAccountsRuleFormType>>({
  mnemonic: [
    {required: true, trigger: 'change', validator: validateMnemonic},
  ],
  accountNum: [
    {required: true, message: 'Please input receiver address', trigger: 'change'},
  ],
})

const onTx = (formEl: FormInstance | undefined) => {
  state.dialogVisible = true
  if (!formEl) return
  formEl.resetFields()
}
const onSenderChange = (value: any) => {
  const sender = state.tableData.find((item) => item.address === value)
  if (sender === undefined) {
    state.senderKeyDisabled = false
  } else {
    state.senderKeyDisabled = true
    sendTXRulesForm.senderKey = sender?.private_key
    sendTXRulesForm.nonce = sender?.nonce
  }
}
const onRestoreAccounts = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  await formEl.validate(async (valid, fields) => {
    if (valid) {
      state.loading = true
      try {
        const res = await reqRestoreAccounts(restoreAccountsFormInline)
        if (res.status) {
          state.tableData = res.data
          globalStore.setRestoreAccountsList(res.data)
        } else {
          throw Error(res.message)
        }
      } catch (e) {
        ElNotification({
          type: 'error',
          message: e
        } as any)
      } finally {
        state.loading = false
      }
    } else {
      ElNotification({
        type: 'error',
        message: fields
      } as any)
    }
  })
}

onMounted(() => {
  window.setInterval(() => {
    update_balance(provider, state.tableData)
  }, 1000)
})
</script>

<template>
  <el-breadcrumb separator="/" style="padding-bottom: 10px">
    <el-breadcrumb-item :to="{ name: 'wallet' }">
      <h1>Reset your wallet</h1>
    </el-breadcrumb-item>
  </el-breadcrumb>
  <el-row>
    <el-col>
      <el-card style="width: 100%">
        <el-row>
          <el-col>
            <el-alert type="warning" effect="dark" :description="alertDesc" show-icon :closable="false"/>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="24">
            <el-form ref="restoreAccountsFormRef"
                     :rules="restoreAccountsRules"
                     size="large"
                     :inline="true"
                     :model="restoreAccountsFormInline"
                     class="demo-form-inline"
            >
              <el-form-item label="Mnemonic Phrase" prop="mnemonic">
                <el-input v-model="restoreAccountsFormInline.mnemonic"
                          size="large"
                          placeholder="Please input a private key mnemonic phrase containing 12 words" clearable/>
              </el-form-item>
              <el-form-item label="Account Number" prop="accountNum">
                <el-input-number size="large" v-model="restoreAccountsFormInline.accountNum"/>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" class="btn" size="large" :disabled="state.loading"
                           @click="onRestoreAccounts(restoreAccountsFormRef)">
                  Restore Accounts
                </el-button>
              </el-form-item>
            </el-form>
          </el-col>
        </el-row>
      </el-card>
    </el-col>
  </el-row>
  <el-row>
    <el-col>
      <el-card class="table" style="width: 100%" max-height="1200">
        <template #header>
          <div class="card-header">
            <span>Accounts</span>
            <el-button class="btn" type="text" size="large" @click="onTx(sendTXFormRef)">Send Transaction</el-button>
          </div>
        </template>
        <el-table :data="state.tableData" :max-height="styleExports.tHeight" v-loading="state.loading"
                  label-width="auto">
          <el-table-column prop="address" label="Account No" :show-overflow-tooltip="true"/>
          <el-table-column prop="name" label="Name"/>
          <el-table-column prop="private_key" label="Private key" :show-overflow-tooltip="true"/>
          <el-table-column prop="balance" label="Balance"/>
          <el-table-column prop="nonce" label="Nonce"/>
        </el-table>
      </el-card>
    </el-col>
  </el-row>
  <el-dialog
      v-model="state.dialogVisible"
      :title="state.dialogTitle"
      width="1000"
      draggable
      :modal="false"
      :lock-scroll="false"
  >
    <el-form
        ref="sendTXFormRef"
        :model="sendTXRulesForm"
        :rules="sendTXRules"
        label-width="auto"
        size="large"
    >
      <el-form-item label="Sender" prop="sender">
        <el-select
            clearable filterable allow-create
            v-model="sendTXRulesForm.sender" placeholder="Please input sender address"
            @change="onSenderChange"
        >
          <el-option v-for="(item, index) in state.tableData" :label="item.address" :value="item.address" :key="index"/>
        </el-select>
      </el-form-item>
      <el-form-item label="Receiver" prop="receiver">
        <el-select
            clearable filterable allow-create
            v-model="sendTXRulesForm.receiver" placeholder="Please input receiver address"
        >
          <el-option v-for="(item, index) in state.tableData" :label="item.address" :value="item.address" :key="index"/>
        </el-select>
      </el-form-item>
      <el-form-item label="senderKey" prop="senderKey">
        <el-input v-model="sendTXRulesForm.senderKey" :disabled="state.senderKeyDisabled"/>
      </el-form-item>
      <el-form-item label="Amount" prop="amount">
        <el-input-number :precision="2" :step="1" v-model="sendTXRulesForm.amount" :min="1"/>
      </el-form-item>
      <div class="btn">
        <el-form-item class="btn">
          <el-button type="primary" @click="onSubmitSendTXForm(sendTXFormRef)">
            Confirm
          </el-button>
          <el-button @click="resetForm(sendTXFormRef)">Cancel</el-button>
        </el-form-item>
      </div>
    </el-form>
  </el-dialog>
</template>

<style scoped lang="scss">
.el-row:not(:first-child) {
  margin-top: 30px;
}

.el-alert {
  :deep(.el-alert__description) {
    font-size: 30px;
  }
}

.words {
  .el-input {
    font-size: 20px;
    color: #0a53be;
  }

  .btn {
    width: 100%;
  }
}

.table {
  .el-table {
    font-size: 20px;
    width: $el-table-width;
    min-height: $el-table-min-height;
    margin-bottom: $el-table-margin-bottom;
  }

  .btn {
    font-size: 30px;
  }

  .card-header {
    text-align: left;
    font-size: 30px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.el-dialog {
  .el-form {
    .el-form-item {
      :deep(.el-form-item__label) {
        font-size: 20px;
      }
    }

    .btn {
      display: flex;
      justify-content: flex-end;

      .el-form-item {
        margin-bottom: 0;
      }
    }
  }
}

.demo-form-inline {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;

  :deep(.el-form-item__label) {
    font-size: 20px;
  }

  :deep(.el-input) {
    --el-input-width: 1300px;
  }

  @media (max-width: 1800px) {
    :deep(.el-input) {
      --el-input-width: 500px;
    }
  }
}
</style>
