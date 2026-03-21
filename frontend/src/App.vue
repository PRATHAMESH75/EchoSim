<template>
  <router-view />
</template>

<script setup>
// Root shell is managed by route views.
</script>

<style>
:root {
  font-family: 'Space Grotesk', sans-serif;
  color: #1f1712;
  background: #fcfaf6;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body,
button,
input,
textarea,
select {
  font-family: 'Space Grotesk', sans-serif;
}

code,
pre,
.mono {
  font-family: 'IBM Plex Mono', monospace;
}

body {
  min-width: 320px;
  background: #fcfaf6;
}

#app {
  min-height: 100vh;
}

button {
  font: inherit;
}

::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

::-webkit-scrollbar-track {
  background: rgba(31, 23, 18, 0.06);
}

::-webkit-scrollbar-thumb {
  background: rgba(31, 23, 18, 0.32);
  border-radius: 999px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(31, 23, 18, 0.48);
}
</style>
