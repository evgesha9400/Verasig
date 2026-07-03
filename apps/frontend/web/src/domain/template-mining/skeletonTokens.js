/* Verasig — Template Mining: skeleton tokenizer.
   Shared by specificity and subsumption scoring, both of which walk a
   normalized skeleton (template.js) token by token: a <*> wildcard, a
   <PLACEHOLDER>, or a structural word/digit run. */

export const TOKEN = /<\*>|<[A-Z_]+>|[\p{L}\p{N}]+/gu
