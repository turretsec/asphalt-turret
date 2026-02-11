<script lang="ts" setup>
import Toolbar from 'primevue/toolbar';
import SearchBox from './toolbar/SearchBox.vue';

const props = defineProps<{
  query: string;
}>();

const emit = defineEmits<{
  (e: "update:query", value: string): void;
}>();

</script>

<template>
    <Toolbar class="flex w-full bg-primary border-b border-surface-700">
        <template #start>
            Start
        </template>
        <template #center>
                <SearchBox 
                    :query="props.query"
                    @update:query="(v) => emit('update:query', String(v))"
                />
        </template>
        <template #end>
            End
        </template>
    </Toolbar>
</template>