<template>
  <div class="home">
    <h1>Welcome to Vue + Flask App </h1>
    <h2>404</h2>
    <p>This is the home page served by Vue.js with Flask backend</p>
    <button @click="fetchData">Test API Call</button>
    <p v-if="apiResponse">{{ apiResponse }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const apiResponse = ref<string>('')

const fetchData = async () => {
  try {
    const response = await fetch('/api/data')
    const data = await response.json()
    apiResponse.value = JSON.stringify(data)
  } catch (error) {
    apiResponse.value = 'Error fetching data'
  }
}
</script>