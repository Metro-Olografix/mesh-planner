/// <reference types="vite/client" />

declare module 'georaster' {
  const parseGeoraster: (data: ArrayBuffer | string) => Promise<any>
  export default parseGeoraster
}

declare module '*.png' {
  const src: string
  export default src
}
