<script setup lang="ts" xmlns="http://www.w3.org/1999/html">

import {onMounted} from "vue";
import {Terminal} from 'xterm';
import {initConsole} from "@/view/console/console.ts"
import type {IframeQueryData} from "@/types";


const parseQueryData = <T>(queryString: string, key: string): T | null => {
  const params = new URLSearchParams(queryString)
  const raw = params.get(key)

  if (!raw) return null

  try {
    return JSON.parse(raw) as T
  } catch (e) {
    console.warn(`query ${key} JSON parse failed`, e)
    return null
  }
}

onMounted(async () => {
  const term = new Terminal({
    theme: {
      foreground: '#C5C8C6',
      background: '#1D1F21',
      cursor: '#C5C8C6',
      cursorAccent: '#C5C8C6',
      black: '#555555',
      red: '#CC6666',
      green: '#B5BD68',
      yellow: '#F0C674',
      blue: '#81A2BE',
      magenta: '#B294BB',
      cyan: '#8ABEB7',
      white: '#C5C8C6'
    }
  });

  term.open(document.getElementById('terminal')!);

  const hash = window.location.hash.replace('#', '');
  const [id, queryString] = hash.split('?')
  const queryData = parseQueryData<IframeQueryData>(queryString || '', 'data')
  const cmd = queryData?.cmd || ''
  const ws = await initConsole(id!, term, cmd)
  window.addEventListener('message', (e) => {
    if (!ws) {
      return
    }
    const msg = e.data
    if (msg?.type === 'DEMO_SYSTEM_CTRL') {
      if (msg?.cmd && msg?.cmd.trim() !== '') {
        setTimeout(() => {
          ws.send(`${msg?.cmd}\n`)
        }, 1000)
      }
    }
  })
})
</script>

<template>
  <div class="container">
    <div class="terminal" id="terminal"></div>
  </div>
</template>

<style scoped lang="scss">
@use '@/style/console/console.css' as *;

</style>