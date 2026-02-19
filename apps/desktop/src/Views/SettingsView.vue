<script setup lang="ts">
import SettingsSection from "../components/settings/SettingsSection.vue";
import SettingsItem from "../components/settings/SettingsItem.vue";

import Button from "primevue/button";
import Select from "primevue/select";
import InputText from "primevue/inputtext";
import InputNumber from "primevue/inputnumber";
import Skeleton from 'primevue/skeleton'; 
import { useConfirm } from 'primevue/useconfirm';

import { useSettingsDraft } from "../composables/useSettingsDraft";

const confirm = useConfirm();

const {
  repoDraft,
  incomingDraft,
  thumbnailQualityDraft,
  thumbnailWidthDraft,
  thumbnailHeightDraft,
  ffprobeTimeoutDraft,
  pickAndSaveDir,
  setNumber,
  resetToDefaults,
  saving,
  query
} = useSettingsDraft();

const qualityOptions = [
  { label: "Low", value: 25 },
  { label: "Medium", value: 65 },
  { label: "High", value: 90 },
];

function handleReset() {
  confirm.require({
    message: 'This will reset all settings to their default values. Are you sure?',
    header: 'Reset to Defaults',
    icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Cancel',
    acceptLabel: 'Reset',
    rejectClass: 'p-button-secondary',
    acceptClass: 'p-button-danger',
    accept: () => {
      resetToDefaults({ includeNumbers: true });
    }
  });
}
</script>


<template>
  <div class="h-full flex flex-col w-full overflow-auto">
    <!-- Header -->
    <div class="flex flex-col w-full p-3 border-b border-surface-800">
      <div class="font-semibold">Settings</div>
      <div class="text-xs opacity-70 mt-1">Customize your application preferences</div>
    </div>

    <!-- Loading State -->
    <div v-if="query.isLoading.value" class="p-6 space-y-8">
      <Skeleton height="8rem" />
      <Skeleton height="8rem" />
      <Skeleton height="8rem" />
    </div>

    <!-- Error State -->
    <div v-if="query.isError.value" class="p-6">
      <EmptyState
        icon="pi pi-exclamation-triangle"
        title="Failed to Load Settings"
        description="Could not connect to the backend. Please check your connection and try again."
        actionLabel="Retry"
        @action="query.refetch"
      />
    </div>

    <!-- Settings Content -->
    <div class="p-6 space-y-8">
      
      <!-- General Section -->
    <SettingsSection
        title="General"
        description="General application settings"
    >
        <!-- Repository Path Setting -->
        <SettingsItem
          label="Repository Path"
          description="Where imported clips are stored"
        >
          <div class="flex gap-2">
            <InputText
              :model-value="repoDraft"
              class="flex-1"
              size="small"
              disabled
            />
            <Button
            icon="pi pi-folder-open"
            size="small"
            severity="secondary"
            :loading="saving"
            @click="() => pickAndSaveDir('repository_dir')"
            />
          </div>
        </SettingsItem>

        <!-- Incoming Directory Setting (if applicable) -->
         <SettingsItem
          label="Incoming Directory"
          description="Where new files from SD cards are stored before processing"
        >
          <div class="flex gap-2">
            <InputText
              :model-value="incomingDraft"
              class="flex-1"
              size="small"
              disabled
            />
            <Button
            icon="pi pi-folder-open"
            size="small"
            severity="secondary"
            :loading="saving"
            @click="() => pickAndSaveDir('incoming_dir')"
            />
          </div>
        </SettingsItem>


      </SettingsSection>

      <!-- Import Section -->
      <!-- <SettingsSection
        title="Import"
        description="Configure how files are imported from SD cards"
      >
        <SettingsItem
          label="Auto-import on connect"
          description="Automatically import new files when SD card is inserted"
        >
          <Switch v-model="effective.autoImportOnConnect" />
        </SettingsItem>

        <SettingsItem
          label="Delete after import"
          description="Remove files from SD card after successful import"
        >
          <Switch v-model="effective.deleteAfterImport" />
        </SettingsItem>
      </SettingsSection> -->

      <!-- Thumbnail Section -->
      <SettingsSection
        title="Thumbnails"
        description="Thumbnail generation settings"
      >
        <SettingsItem
          label="Thumbnail quality"
          description="Higher quality uses more storage space"
        >
            <Select
            :modelValue="thumbnailQualityDraft"
            @update:modelValue="(value) => setNumber('thumbnail_quality', value)"
            :options="qualityOptions"
            optionLabel="label"
            optionValue="value"
            class="w-48"
            size="small"
/>
        </SettingsItem>

        <SettingsItem
          label="Thumbnail width"
          description="Width of generated thumbnails in pixels"
        >
          <InputNumber
            v-model="thumbnailWidthDraft"
            :min="16"
            :max="1920"
            :step="16"
            class="w-48"
            size="small"
            @update:modelValue="(v) => setNumber('thumbnail_width', Number(v ?? 320), false)"
          />
        </SettingsItem>

        <SettingsItem
          label="Thumbnail height"
          description="Height of generated thumbnails in pixels"
        >
        <InputNumber
            v-model="thumbnailHeightDraft"
            :min="16"
            :max="1080"
            :step="16"
            class="w-48"
            size="small"
            @update:modelValue="(v) => setNumber('thumbnail_height', Number(v ?? 180), false)"
          />    
        </SettingsItem>

        <!-- <SettingsItem
          label="Auto-probe metadata"
          description="Automatically extract video metadata on import"
        >
          <Switch v-model="effective.autoProbe" />
        </SettingsItem> -->
      </SettingsSection>

      <SettingsSection
        title="FFprobe"
        description="Settings related to video metadata extraction"
      >

        <SettingsItem
          label="FFprobe timeout"
          description="Maximum time to wait for ffprobe to analyze a video (in seconds)"
        >
          <InputNumber
            v-model="ffprobeTimeoutDraft"
            :min="5"
            :max="120"
            :step="5"
            class="w-48"
            size="small"
            @update:modelValue="(v) => setNumber('ffprobe_timeout_s', Number(v ?? 30), false)"
          />
        </SettingsItem>


      </SettingsSection>

      <!-- Advanced Section -->
      <!-- <SettingsSection
        title="Advanced"
        description="Advanced settings for power users"
      >
        <SettingsItem
          label="Debug mode"
          description="Show additional debugging information"
        >
          <Switch v-model="settings.enableDebugMode" />
        </SettingsItem>

        <SettingsItem
          label="Cache size"
          description="Maximum cache size in megabytes"
        >
          <InputNumber
            v-model="settings.cacheSize"
            suffix=" MB"
            :min="100"
            :max="5000"
            :step="100"
            class="w-48"
          />
        </SettingsItem>
      </SettingsSection> -->

    </div>

    <!-- Footer Actions -->
    <div class="p-6 border-t border-surface-800 flex justify-between">
        <Button
        label="Reset to Defaults"
        icon="pi pi-refresh"
        size="small"
        severity="danger"
        outlined
        :loading="saving"
        @click="handleReset"
        />
      
      <div class="text-sm text-surface-400">
        Changes are saved automatically
      </div>
    </div>
  </div>
</template>