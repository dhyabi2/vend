import { IntegrationDefinition, z } from '@botpress/sdk'

// Vend API Merchant — Botpress integration draft.
// Lets a Botpress bot call a Vend pay-per-call endpoint (extract, web-search)
// settled in Nano (XNO) via x402. No API key required.
//
// Flow: action calls the Vend endpoint -> HTTP 402 with an x402 challenge ->
// the bot/user settles the Nano payment -> block hash is passed back as
// `paymentHeader` -> action retries with X-PAYMENT -> HTTP 200 with the JSON data.
//
// DRAFT only (2026-09-20). Not built/verified with the Botpress CLI or deployed
// to the Botpress Hub. Match against the current Botpress SDK before use.

export default new IntegrationDefinition({
  name: 'vend/vend-api-merchant',
  version: '0.1.0',
  title: 'Vend API Merchant',
  description: 'Pay-per-call web intel and search settled in Nano (XNO) via x402. No API key, no signup.',
  icon: 'icon.svg',
  readme: 'hub.md',
  configuration: {
    schema: z.object({
      baseUrl: z.string().url().default('https://extract.paypercall.dev'),
      // Optional: a settled payment's block hash reused across calls within its window.
      paymentHeader: z.string().optional(),
    }),
  },
  actions: {
    extract: {
      title: 'Extract Web Page',
      description: 'Returns clean text/markdown from a web page. Price: 0.0001 XNO.',
      input: {
        schema: z.object({ url: z.string().url() }),
      },
      output: {
        schema: z.object({
          url: z.string().optional(),
          title: z.string().optional(),
          text: z.string().optional(),
          markdown: z.string().optional(),
          payment_required: z.boolean().optional(),
          price_xno: z.number().optional(),
          pay_to: z.string().optional(),
        }),
      },
    },
    webSearch: {
      title: 'Web Search',
      description: 'Searches the web via DuckDuckGo. Price: 0.0001 XNO.',
      input: {
        schema: z.object({ q: z.string() }),
      },
      output: {
        schema: z.object({
          results: z.array(z.object({ title: z.string(), url: z.string(), snippet: z.string() })).optional(),
          payment_required: z.boolean().optional(),
        }),
      },
    },
  },
})
