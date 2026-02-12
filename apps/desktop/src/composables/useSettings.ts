import { computed } from "vue";
import { useQuery, useMutation, useQueryClient } from "@tanstack/vue-query";
import { getSettings, patchSettings } from "../api/settings";
import type { SettingsResponse, EffectiveSettings, UserSettings } from "../api/types";
import { useToast } from 'primevue/usetoast';

export function useSettings() {
  const qc = useQueryClient();
  const toast = useToast();
  
  const query = useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
    staleTime: Infinity,
  });

  // Type-safe computed
  const effective = computed<EffectiveSettings>(() => 
    query.data.value?.effective ?? {} as EffectiveSettings
  );
  
  const user = computed<UserSettings>(() => 
    query.data.value?.user ?? {} as UserSettings
  );

  const saveMutation = useMutation({
    mutationFn: (patch: Partial<UserSettings>) => patchSettings(patch),
    onSuccess: (data: SettingsResponse) => {
      qc.setQueryData(["settings"], data);
      
      // Optional: Show toast if restart required
      if (data.restart_required) {
        toast.add({
          severity: 'warn',
          summary: 'Restart Required',
          detail: 'Some changes will take effect after restarting the application.',
          life: 5000,
        });
      }
    },
  });

  return {
    query,
    effective,
    user,
    save: saveMutation.mutateAsync,
    saving: saveMutation.isPending,
    lastSaveResult: computed(() => saveMutation.data.value),
  };
}