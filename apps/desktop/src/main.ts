import { createApp } from "vue";
import App from "./App.vue";
import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'

import PrimeVue from "primevue/config";
import Aura from "@primeuix/themes/aura";
import "primeicons/primeicons.css";
import ToastService from 'primevue/toastservice';
import ConfirmationService from 'primevue/confirmationservice';
import "./styles/app.css";
//import "./styles/primevue-overrides.css";
import { definePreset } from "@primeuix/themes";

import Tooltip from 'primevue/tooltip';
import { TooltipStyle } from "primevue";

// TanStack Query

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // 30 seconds default
      retry: 1,                // retry failed requests once
      refetchOnWindowFocus: false,  // desktop app — no tab-switching behaviour needed
    },
  },
})

const app = createApp(App);

const turretTheme = definePreset(Aura, {
  semantic: {
    primary: {
      50: '{violet.50}',
      100: '{violet.100}',
      200: '{violet.200}',
      300: '{violet.300}',
      400: '{violet.400}',
      500: '{violet.500}',
      600: '{violet.600}',
      700: '{violet.700}',
      800: '{violet.800}',
      900: '{violet.900}',
      950: '{violet.950}'
    },
    colorScheme: {
      dark: {
        surface: {
          700: '#2f2a3d',
          750: '#292436',
          800: '#221f2e',
          850: '#1d1a28',
          900: '#181622',
          950: '#12101a',
        }
      }
    }

    // You will also want to override surfaces/neutral scale here
    // (exact key names depend on Aura + PrimeUIX version)
  },
});

app.use(PrimeVue, {
  theme: {
    preset: turretTheme,
    options: {
      cssLayer: {
        name: 'primevue',
        order: 'theme, base, primevue'
      }
    }
  },
  pt: {
    button: {
      root: {
        class: 'rounded-sm shadow-none font-medium tracking-tight focus:outline-none'
      }
    }
  }
});
app.use(ToastService);
app.use(ConfirmationService);
app.use(VueQueryPlugin, { queryClient });
app.directive('tooltip', Tooltip);
app.mount("#app");