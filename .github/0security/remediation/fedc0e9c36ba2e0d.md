# Recommended fixes

Several dependencies need a change that could not be completed automatically. Each entry below names the version to move to and what is left to do.

Use these steps with your coding agent. This draft contains guidance only. The findings remain open until the change is reviewed.

Source revision: 397ab07383c97305328a8cebfedbd35b1ff8b7d6

## Affected dependencies

- aiohttp 3\.9\.5 (PyPI) in requirements\.txt. Advisory-listed fixed versions: 3\.10\.11, 3\.12\.14, 3\.13\.3, 3\.13\.4. Automatic updates are not supported for this package manager or lockfile. Prepare and test the update with your coding agent.
- anyio 4\.9\.0 (PyPI) in hfspace\_gradio/requirements\.txt. Advisory-listed fixed versions: 4\.14\.2. A fix is available. Complete the checks needed to verify the update.
- certifi 2026\.7\.22 (PyPI) in hfspace\_gradio/requirements\.txt. Advisory-listed fixed versions: 2026\.10\.18. A fix is available. Complete the checks needed to verify the update.
- certifi 2026\.7\.22 (PyPI) in requirements\.txt. Advisory-listed fixed versions: 2026\.10\.18. Automatic updates are not supported for this package manager or lockfile. Prepare and test the update with your coding agent.
- gradio 6\.9\.0 (PyPI) in hfspace\_gradio/requirements\.txt. Advisory-listed fixed versions: 6\.15\.0, 6\.15\.1, 6\.16\.0. A fix is available. Complete the checks needed to verify the update.
- idna 3\.9\.0 (PyPI) in hfspace\_gradio/requirements\.txt. Advisory-listed fixed versions: 3\.15. A fix is available. Complete the checks needed to verify the update.
- orjson 3\.9\.9 (PyPI) in hfspace\_gradio/requirements\.txt. Advisory-listed fixed versions: 3\.11\.6, 3\.9\.15. A fix is available. Complete the checks needed to verify the update.
- pillow 12\.3\.0 (PyPI) in hfspace\_gradio/requirements\.txt. Advisory-listed fixed versions: 13\.0\.0. A fix is available. Complete the checks needed to verify the update.
- pillow 9\.5\.0 (PyPI) in hfspace\_gradio/requirements\.txt. Advisory-listed fixed versions: 10\.0\.0, 10\.0\.1, 10\.3\.0, 12\.2\.0, 12\.3\.0, 13\.0\.0. A fix is available. Complete the checks needed to verify the update.
- starlette 0\.52\.1 (PyPI) in hfspace\_gradio/requirements\.txt. Advisory-listed fixed versions: 1\.0\.1, 1\.1\.0, 1\.3\.0, 1\.3\.1. A fix is available. Complete the checks needed to verify the update.
- transformers 5\.9\.0 (PyPI) in hfspace\_gradio/requirements\.txt. Advisory-listed fixed versions: 5\.10\.0. A fix is available. Complete the checks needed to verify the update.
- transformers 5\.9\.0 (PyPI) in requirements\.txt. Advisory-listed fixed versions: 5\.10\.0. Automatic updates are not supported for this package manager or lockfile. Prepare and test the update with your coding agent.

## Advisories

- [GHSA\-22hg\-r758\-rrw9](https://osv.dev/vulnerability/GHSA-22hg-r758-rrw9)
- [GHSA\-24rc\-8hj2\-v98c](https://osv.dev/vulnerability/GHSA-24rc-8hj2-v98c)
- [GHSA\-27h8\-gf7j\-v5hc](https://osv.dev/vulnerability/GHSA-27h8-gf7j-v5hc)
- [GHSA\-2vrm\-gr82\-f7m5](https://osv.dev/vulnerability/GHSA-2vrm-gr82-f7m5)
- [GHSA\-3j72\-p6qg\-6xp7](https://osv.dev/vulnerability/GHSA-3j72-p6qg-6xp7)
- [GHSA\-3wq7\-rqq7\-wx6j](https://osv.dev/vulnerability/GHSA-3wq7-rqq7-wx6j)
- [GHSA\-44wm\-f244\-xhp3](https://osv.dev/vulnerability/GHSA-44wm-f244-xhp3)
- [GHSA\-4558\-3h8r\-v8xp](https://osv.dev/vulnerability/GHSA-4558-3h8r-v8xp)
- [GHSA\-45hq\-cxwh\-f6vc](https://osv.dev/vulnerability/GHSA-45hq-cxwh-f6vc)
- [GHSA\-4rm8\-3hmm\-39fg](https://osv.dev/vulnerability/GHSA-4rm8-3hmm-39fg)
- [GHSA\-4rr5\-89j8\-mwwm](https://osv.dev/vulnerability/GHSA-4rr5-89j8-mwwm)
- [GHSA\-4x4j\-2g7c\-83w6](https://osv.dev/vulnerability/GHSA-4x4j-2g7c-83w6)
- [GHSA\-54jq\-c3m8\-4m76](https://osv.dev/vulnerability/GHSA-54jq-c3m8-4m76)
- [GHSA\-58r4\-6rv3\-gfh8](https://osv.dev/vulnerability/GHSA-58r4-6rv3-gfh8)
- [GHSA\-5p39\-cfhj\-2xmp](https://osv.dev/vulnerability/GHSA-5p39-cfhj-2xmp)
- [GHSA\-5x8w\-8jj5\-q52h](https://osv.dev/vulnerability/GHSA-5x8w-8jj5-q52h)
- [GHSA\-5x94\-69rx\-g8h2](https://osv.dev/vulnerability/GHSA-5x94-69rx-g8h2)
- [GHSA\-62p4\-gmf7\-7g93](https://osv.dev/vulnerability/GHSA-62p4-gmf7-7g93)
- [GHSA\-63hf\-3vf5\-4wqf](https://osv.dev/vulnerability/GHSA-63hf-3vf5-4wqf)
- [GHSA\-654x\-cwwv\-5j9c](https://osv.dev/vulnerability/GHSA-654x-cwwv-5j9c)
- [GHSA\-65pc\-fj4g\-8rjx](https://osv.dev/vulnerability/GHSA-65pc-fj4g-8rjx)
- [GHSA\-6655\-8ph2\-63j3](https://osv.dev/vulnerability/GHSA-6655-8ph2-63j3)
- [GHSA\-69f9\-5gxw\-wvc2](https://osv.dev/vulnerability/GHSA-69f9-5gxw-wvc2)
- [GHSA\-6jhg\-hg63\-jvvf](https://osv.dev/vulnerability/GHSA-6jhg-hg63-jvvf)
- [GHSA\-6mq8\-rvhq\-8wgg](https://osv.dev/vulnerability/GHSA-6mq8-rvhq-8wgg)
- [GHSA\-6q48\-6c7w\-9gw2](https://osv.dev/vulnerability/GHSA-6q48-6c7w-9gw2)
- [GHSA\-6r8x\-57c9\-28j4](https://osv.dev/vulnerability/GHSA-6r8x-57c9-28j4)
- [GHSA\-7hp7\-4p35\-3cx2](https://osv.dev/vulnerability/GHSA-7hp7-4p35-3cx2)
- [GHSA\-7mwm\-ghpf\-9vrm](https://osv.dev/vulnerability/GHSA-7mwm-ghpf-9vrm)
- [GHSA\-82r6\-8w77\-94w6](https://osv.dev/vulnerability/GHSA-82r6-8w77-94w6)
- [GHSA\-82w8\-qh3p\-5jfq](https://osv.dev/vulnerability/GHSA-82w8-qh3p-5jfq)
- [GHSA\-8495\-4g3g\-x7pr](https://osv.dev/vulnerability/GHSA-8495-4g3g-x7pr)
- [GHSA\-86qp\-5c8j\-p5mr](https://osv.dev/vulnerability/GHSA-86qp-5c8j-p5mr)
- [GHSA\-8g5g\-8vmr\-9782](https://osv.dev/vulnerability/GHSA-8g5g-8vmr-9782)
- [GHSA\-8ghj\-p4vj\-mr35](https://osv.dev/vulnerability/GHSA-8ghj-p4vj-mr35)
- [GHSA\-8v84\-f9pq\-wr9x](https://osv.dev/vulnerability/GHSA-8v84-f9pq-wr9x)
- [GHSA\-9548\-qrrj\-x5pj](https://osv.dev/vulnerability/GHSA-9548-qrrj-x5pj)
- [GHSA\-966j\-vmvw\-g2g9](https://osv.dev/vulnerability/GHSA-966j-vmvw-g2g9)
- [GHSA\-9hw9\-ch79\-4vh6](https://osv.dev/vulnerability/GHSA-9hw9-ch79-4vh6)
- [GHSA\-9v9v\-9qvf\-h2hj](https://osv.dev/vulnerability/GHSA-9v9v-9qvf-h2hj)
- [GHSA\-c427\-h43c\-vf67](https://osv.dev/vulnerability/GHSA-c427-h43c-vf67)
- [GHSA\-cp9v\-662q\-vvx9](https://osv.dev/vulnerability/GHSA-cp9v-662q-vvx9)
- [GHSA\-fh55\-r93g\-j68g](https://osv.dev/vulnerability/GHSA-fh55-r93g-j68g)
- [GHSA\-fj7v\-r99m\-22gq](https://osv.dev/vulnerability/GHSA-fj7v-r99m-22gq)
- [GHSA\-g4qv\-2jxx\-769h](https://osv.dev/vulnerability/GHSA-g4qv-2jxx-769h)
- [GHSA\-g842\-9rc4\-69pw](https://osv.dev/vulnerability/GHSA-g842-9rc4-69pw)
- [GHSA\-g84x\-mcqj\-x9qq](https://osv.dev/vulnerability/GHSA-g84x-mcqj-x9qq)
- [GHSA\-hcc4\-c3v8\-rx92](https://osv.dev/vulnerability/GHSA-hcc4-c3v8-rx92)
- [GHSA\-hx9q\-6w63\-j58v](https://osv.dev/vulnerability/GHSA-hx9q-6w63-j58v)
- [GHSA\-j36p\-7w88\-g82j](https://osv.dev/vulnerability/GHSA-j36p-7w88-g82j)
- [GHSA\-j7hp\-h8jx\-5ppr](https://osv.dev/vulnerability/GHSA-j7hp-h8jx-5ppr)
- [GHSA\-jj3x\-wxrx\-4x23](https://osv.dev/vulnerability/GHSA-jj3x-wxrx-4x23)
- [GHSA\-jjj6\-mw9f\-p565](https://osv.dev/vulnerability/GHSA-jjj6-mw9f-p565)
- [GHSA\-jp82\-jpqv\-5vv3](https://osv.dev/vulnerability/GHSA-jp82-jpqv-5vv3)
- [GHSA\-m5qp\-6w8w\-w647](https://osv.dev/vulnerability/GHSA-m5qp-6w8w-w647)
- [GHSA\-mqqc\-3gqh\-h2x8](https://osv.dev/vulnerability/GHSA-mqqc-3gqh-h2x8)
- [GHSA\-mwh4\-6h8g\-pg8w](https://osv.dev/vulnerability/GHSA-mwh4-6h8g-pg8w)
- [GHSA\-p8hx\-v2p6\-rp84](https://osv.dev/vulnerability/GHSA-p8hx-v2p6-rp84)
- [GHSA\-p998\-jp59\-783m](https://osv.dev/vulnerability/GHSA-p998-jp59-783m)
- [GHSA\-pchr\-8j38\-3x4p](https://osv.dev/vulnerability/GHSA-pchr-8j38-3x4p)
- [GHSA\-phj9\-mv4w\-65pm](https://osv.dev/vulnerability/GHSA-phj9-mv4w-65pm)
- [GHSA\-pwr2\-4v36\-6qpr](https://osv.dev/vulnerability/GHSA-pwr2-4v36-6qpr)
- [GHSA\-r73j\-pqj5\-w3x7](https://osv.dev/vulnerability/GHSA-r73j-pqj5-w3x7)
- [GHSA\-v9pv\-5gc8\-w2m6](https://osv.dev/vulnerability/GHSA-v9pv-5gc8-w2m6)
- [GHSA\-vjc4\-5qp5\-m44j](https://osv.dev/vulnerability/GHSA-vjc4-5qp5-m44j)
- [GHSA\-w2fm\-2cpv\-w7v5](https://osv.dev/vulnerability/GHSA-w2fm-2cpv-w7v5)
- [GHSA\-wjx4\-4jcj\-g98j](https://osv.dev/vulnerability/GHSA-wjx4-4jcj-g98j)
- [GHSA\-wqp7\-x3pw\-xc5r](https://osv.dev/vulnerability/GHSA-wqp7-x3pw-xc5r)
- [GHSA\-x746\-7m8f\-x49c](https://osv.dev/vulnerability/GHSA-x746-7m8f-x49c)
- [GHSA\-xgh8\-jp6q\-p5x8](https://osv.dev/vulnerability/GHSA-xgh8-jp6q-p5x8)
- [GHSA\-xj96\-63gp\-2gmr](https://osv.dev/vulnerability/GHSA-xj96-63gp-2gmr)
- [GHSA\-xrqw\-3rrv\-vx5w](https://osv.dev/vulnerability/GHSA-xrqw-3rrv-vx5w)
- [PYSEC\-2023\-175](https://osv.dev/vulnerability/PYSEC-2023-175)

## Steps for your coding agent

### Automatic updates are not supported for this package manager or lockfile. Prepare and test the update with your coding agent.

1. Use this ecosystem's package manager to inspect available fixed versions and dependency constraints.
2. Prepare an update or mitigation manually, including any required application changes.
3. Run the project's tests and recheck the advisory.

### A fix is available. Complete the checks needed to verify the update.

1. Review installation, build and test failures from the Security test.
2. Reproduce the failures locally and correct the update in a separate change.
3. Confirm tests pass and the advisory no longer affects the installed version.

Keep the finding open until an update or mitigation has been reviewed.
