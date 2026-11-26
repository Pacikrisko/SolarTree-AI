const cardArt: Record<string,string> = {
  'IVAN-TREE-0001':'prototype',
  'SOLIX-ARC-0001':'urban-straight',
  'SOLIX-HALO-0002':'urban-curved',
}

export function cardImage(code:string){
  const name=cardArt[code]
  return name ? `/tree-cards/${name}.png` : null
}
