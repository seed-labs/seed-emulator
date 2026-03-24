<template>
  <el-upload
      ref="upload"
      drag
      :limit="1"
      :on-exceed="handleExceed"
      :auto-upload="false"
      :on-change="handleFileChange"
      accept=".yml,.yaml,.json"
  >
    <template #trigger>
      <el-icon class="el-icon--upload">
        <upload-filled/>
      </el-icon>
      <div class="el-upload__text">
        Drop file here or <em>click to upload</em>
      </div>
    </template>
<!--    <template #tip>-->
<!--      <div class="el-upload__tip">-->
<!--        Supported files: docker-compose.yml, docker-compose.yaml, *.json-->
<!--      </div>-->
<!--    </template>-->
    <div style="display: flex; justify-content: flex-end; margin-top: 10px;">
      <el-button class="ml-3" type="success" @click="parseFile" :loading="loading">
        {{ loading ? 'During file parsing...' : 'Parse file' }}
      </el-button>
      <el-button class="ml-3" type="info" @click="clearFile" v-if="currentFile">
        Clear
      </el-button>
    </div>
  </el-upload>
</template>

<script setup lang="ts">
import {ref} from 'vue'
import yaml from 'js-yaml'
import type {UploadInstance, UploadProps, UploadRawFile} from 'element-plus'
import {ElMessage, genFileId, UploadFile} from 'element-plus'
import {UploadFilled} from '@element-plus/icons-vue'
import {genVisData} from "@/utils/tools.ts"

interface Props {
  mapData: any
}

withDefaults(defineProps<Props>(), {})
const emit = defineEmits(['update:mapData',]);

const upload = ref<UploadInstance>()
const loading = ref(false)
const currentFile = ref<File | null>(null)
const processedData = ref<any>(null)
const fileType = ref<'yaml' | 'json' | null>(null)
const handleExceed: UploadProps['onExceed'] = (files) => {
  upload.value!.clearFiles()
  const file = files[0] as UploadRawFile
  file.uid = genFileId()
  upload.value!.handleStart(file)
}

const handleFileChange = (file: UploadFile) => {
  if (file.raw) {
    currentFile.value = file.raw
    processedData.value = null
    fileType.value = null
  }
}

const parseFileContent = (file: File): Promise<any> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    const fileName = file.name.toLowerCase()

    reader.onload = (e) => {
      try {
        let parsed
        const content = e.target?.result as string
        const parts = fileName.split('.')
        const suffix = parts[parts.length - 1]!.toLowerCase()
        switch (suffix) {
          case 'yml' || 'yaml':
            parsed = yaml.load(content)
            parsed = genVisData(parsed!)
            fileType.value = 'json'
            resolve({
              type: 'json',
              fileName: file.name,
              content: parsed,
              raw: content
            })
            break
          case 'json':
            parsed = JSON.parse(content)
            fileType.value = 'json'
            resolve({
              type: 'json',
              fileName: file.name,
              content: parsed,
              raw: content
            })
            break
          default:
            reject(new Error('Unsupported file type'))
        }
      } catch (error: any) {
        reject(new Error(`Parsing failed: ${error.message}`))
      }
    }

    reader.onerror = () => reject(new Error('File reading failed'))
    reader.readAsText(file)
  })
}

const parseFile = async () => {
  if (!currentFile.value) {
    ElMessage.warning('Please select the file first.')
    return
  }

  loading.value = true

  try {
    ElMessage.info('Parsing file...')
    const fileData = await parseFileContent(currentFile.value)
    if (fileData.content) {
      emit('update:mapData', fileData.content)
    }
  } catch (error: any) {
    console.error('File parsing failed:', error)
    ElMessage.error(error.message || 'File parsing failed')
    processedData.value = null
  } finally {
    loading.value = false
  }
}

const clearFile = () => {
  upload.value?.clearFiles()
  currentFile.value = null
  processedData.value = null
  fileType.value = null
}
</script>