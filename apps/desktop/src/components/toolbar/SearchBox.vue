<script lang="ts" setup>
import IconField from 'primevue/iconfield';
import InputIcon from 'primevue/inputicon';
import InputText from 'primevue/inputtext';

const props = defineProps<{
  query: string;
}>();

const emit = defineEmits<{
  (e: "update:query", value: string): void;
}>();
</script>

<template>
    <IconField>
        <InputIcon>
            <i class="pi pi-search" />
        </InputIcon>
        <InputText 
            placeholder="Search"
            size="small"
            v-model:model-value="props.query"
            @update:model-value="(v) => emit('update:query', String(v))"
        />
    </IconField>
</template>