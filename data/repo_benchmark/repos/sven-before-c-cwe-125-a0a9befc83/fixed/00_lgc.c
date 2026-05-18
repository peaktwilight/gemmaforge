static void youngcollection (lua_State *L, global_State *g) {
  GCObject **psurvival;  /* to point to first non-dead survival object */
  lua_assert(g->gcstate == GCSpropagate);
  markold(g, g->allgc, g->reallyold);
  markold(g, g->finobj, g->finobjrold);
  atomic(L);

  /* sweep nursery and get a pointer to its last live element */
  psurvival = sweepgen(L, g, &g->allgc, g->survival);
  /* sweep 'survival' and 'old' */
  sweepgen(L, g, psurvival, g->reallyold);
  g->reallyold = g->old;
  g->old = *psurvival;  /* 'survival' survivals are old now */
  g->survival = g->allgc;  /* all news are survivals */

  /* repeat for 'finobj' lists */
  psurvival = sweepgen(L, g, &g->finobj, g->finobjsur);
  /* sweep 'survival' and 'old' */
  sweepgen(L, g, psurvival, g->finobjrold);
  g->finobjrold = g->finobjold;
  g->finobjold = *psurvival;  /* 'survival' survivals are old now */
  g->finobjsur = g->finobj;  /* all news are survivals */

  sweepgen(L, g, &g->tobefnz, NULL);

  finishgencycle(L, g);
}
