# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function)

try:
    import numpy as np
except ImportError:
    np = None

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from .. import ReactionSystem, Equilibrium


def _dominant_reaction_effects(substance_key, rsys, rates, linthreshy, eqk1, eqk2, eqs):
    tot = np.zeros(rates.shape[0])
    reaction_effects = rsys.per_reaction_effect_on_substance(substance_key)
    data = []
    for ri, n in reaction_effects.items():
        tot += n*rates[..., ri]
        if ri in eqk1:
            otheri = eqk2[eqk1.index(ri)]
            y = n*rates[..., ri] + reaction_effects[otheri]*rates[..., otheri]
            rxn = eqs[eqk1.index(ri)]
        elif ri in eqk2:
            continue
        else:
            y = n*rates[..., ri]
            rxn = rsys.rxns[ri]
        if np.all(np.abs(y) < linthreshy):
            continue
        data.append((y, rxn))
    return data, tot


def _combine_rxns_to_eq(rsys):
    eqk1, eqk2 = zip(*rsys.identify_equilibria())
    eqs = [Equilibrium(rsys.rxns[ri].reac,
                       rsys.rxns[ri].prod,
                       inact_reac=rsys.rxns[ri].inact_reac,
                       inact_prod=rsys.rxns[ri].inact_prod) for ri in eqk1]
    return eqk1, eqk2, eqs


def plot_reaction_contributions(varied, concs, rate_exprs_cb, rsys, substance_keys=None, axes=None,
                                total=False, linthreshy=1e-9, relative=False, xscale='log', yscale='symlog',
                                xlabel='Time', ylabel=None, combine_equilibria=False):
    """ Plots per reaction contributions to concentration evolution of a substance.

    Parameters
    ----------
    result : pyodesys.results.Result
    substance_key : str

    """
    if concs.shape[0] != varied.size:
        raise ValueError("Size mismatch between varied and concs")
    if substance_keys is None:
        substance_keys = rsys.substances.keys()
    if axes is None:
        _fig, axes = plt.subplots(len(substance_keys))
    rates = rate_exprs_cb(np.zeros(concs.shape[0]), concs)
    eqk1, eqk2, eqs = _combine_rxns_to_eq(rsys) if combine_equilibria else ([], [], [])

    for sk, ax in zip(substance_keys, axes):
        data, tot = _dominant_reaction_effects(sk, rsys, rates, linthreshy, eqk1, eqk2, eqs)
        factor = 1/concs[:, rsys.as_substance_index(sk)] if relative else 1
        if total:
            ax.plot(varied, factor*tot, c='k', label='Total', linewidth=2, ls=':')
        for y, rxn in sorted(data, key=lambda args: args[0][-1], reverse=True):
            ax.plot(varied, factor*y,
                    label=r'$\mathrm{%s}$' % rxn.latex(rsys.substances))

        if rsys.substances[sk].latex_name is None:
            ttl = rsys.substances[sk].name
            ttl_template = '%s'
        else:
            ttl = rsys.substances[sk].latex_name
            ttl_template = r'\mathrm{$%s$}'

        if yscale == 'symlog':
            ax.axhline(linthreshy, linestyle='--', color='k', linewidth=.5)
            ax.axhline(-linthreshy, linestyle='--', color='k', linewidth=.5)
            ax.set_yscale(yscale, linthreshy=linthreshy)
        else:
            ax.set_yscale(yscale)

        if ylabel is None:
            ax.set_ylabel(r'$\frac{d}{dt}\left[%s\right]\ /\ M\cdot s^{-1}$' % ttl)
        else:
            ax.set_ylabel(ylabel)
            ax.set_title(ttl_template % ttl)

        ax.set_xlabel(xlabel)
        ax.set_xscale(xscale)
        ax.legend(loc='best')


def dominant_reactions_graph(concs, rate_exprs_cb, rsys, substance_key, linthreshy=1e-9,
                             fname='dominant_reactions_graph.png', relative=False,
                             combine_equilibria=False, **kwargs):
    from ..util.graph import rsys2graph
    rates = rate_exprs_cb(0, concs)
    eqk1, eqk2, eqs = _combine_rxns_to_eq(rsys) if combine_equilibria else ([], [], [])
    rrate, rxns = zip(*_dominant_reaction_effects(substance_key, rsys, rates, linthreshy, eqk1, eqk2, eqs)[0])
    rsys = ReactionSystem(rxns, rsys.substances, rsys.name)
    lg_rrate = np.log10(np.abs(rrate))
    rsys2graph(rsys, fname=fname, penwidths=1 + lg_rrate - np.min(lg_rrate), **kwargs)
