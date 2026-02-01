<script setup lang="ts" xmlns="http://www.w3.org/1999/html">

import {onMounted} from "vue";
import {Terminal} from 'xterm';
import {initConsole} from "@/view/console/console.ts"


onMounted(() => {
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

  term.open(document.getElementById('terminal'));

  const id = window.location.hash.replace('#', '');
  initConsole(id, term)
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