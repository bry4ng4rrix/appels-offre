/** L'adresse de la fiche d'une offre (les identifiants peuvent contenir des « / »). */
export const lienOffre = (id: string) => `/offres/${id.split("/").map(encodeURIComponent).join("/")}`
