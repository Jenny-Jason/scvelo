from ..tools.utils import groups_to_bool
from .utils import default_basis, default_size, savefig_or_show, \
    default_color, make_unique_list, make_unique_valid_list, get_components
from .scatter import scatter
from .docs import doc_scatter, doc_params

from matplotlib import rcParams
import matplotlib.pyplot as pl
import numpy as np
from inspect import signature

from scanpy.plotting._tools.paga import paga as scanpy_paga


@doc_params(scatter=doc_scatter)
def paga(adata, basis=None, vkey='velocity', color=None, layer=None, title=None, threshold=None, layout=None,
         layout_kwds={}, init_pos=None, root=0, labels=None, single_component=False, dashed_edges='connectivities',
         solid_edges='transitions_confidence', transitions='transitions_confidence', node_size_scale=1, node_size_power=0.5,
         edge_width_scale=.4, min_edge_width=None, max_edge_width=2, arrowsize=15, random_state=0, pos=None,
         node_colors=None, normalize_to_color=False, cmap=None, cax=None, cb_kwds={}, add_pos=True,
         export_to_gexf=False, plot=True, use_raw=None, size=None, groups=None, components=None, figsize=None, dpi=None,
         show=True, save=None, ax=None, ncols=None, scatter_flag=None, **kwargs):
    """\
    PAGA plot on the embedding.
    Arguments
    ---------
    adata: :class:`~anndata.AnnData`
        Annotated data matrix.
    vkey: `str` or `None` (default: `None`)
        Key for annotations of observations/cells or variables/genes.
    {scatter}
    Returns
    -------
        `matplotlib.Axis` if `show==False`
    """

    if scatter_flag is None:
        scatter_flag = ax is None
    vkey = [key for key in adata.layers.keys() if 'velocity' in key and '_u' not in key] if vkey == 'all' else vkey
    layers, vkeys, colors = make_unique_list(layer), make_unique_list(vkey), make_unique_list(color, allow_array=True)
    node_colors = colors if node_colors is None else node_colors
    bases = [default_basis(adata) if basis is None else basis for basis in make_unique_valid_list(adata, basis)]
    if transitions not in adata.uns['paga']: transitions = None
    if min_edge_width is not None: max_edge_width = max(min_edge_width, max_edge_width)

    if threshold is None and 'threshold' in adata.uns['paga']: threshold = adata.uns['paga']['threshold']
    paga_kwargs = {'threshold': threshold, 'layout': layout, 'layout_kwds': layout_kwds, 'init_pos': init_pos,
                   'root': root, 'labels': labels, 'single_component': single_component,
                   'solid_edges': solid_edges, 'dashed_edges': dashed_edges, 'transitions': transitions,
                   'node_size_scale': node_size_scale, 'node_size_power': node_size_power,
                   'edge_width_scale': edge_width_scale, 'min_edge_width': min_edge_width,
                   'max_edge_width': max_edge_width, 'arrowsize': arrowsize, 'random_state': random_state,
                   'pos': pos, 'normalize_to_color': normalize_to_color, 'cmap': cmap, 'cax': cax, 'cb_kwds': cb_kwds,
                   'add_pos': add_pos, 'export_to_gexf': export_to_gexf, 'colors': node_colors, 'plot': plot}

    for key in kwargs:
        if key in signature(scanpy_paga).parameters:
            paga_kwargs[key] = kwargs[key]
    kwargs = {k: v for k, v in kwargs.items() if k in signature(scatter).parameters}

    if isinstance(node_colors, dict):  # has to be disabled
        paga_kwargs['colorbar'] = False

    multikey = colors if len(colors) > 1 else layers if len(layers) > 1 \
        else vkeys if len(vkeys) > 1 else bases if len(bases) > 1 else None
    if multikey is not None:
        if title is None:
            title = list(multikey)
        elif isinstance(title, (list, tuple)):
            title *= int(np.ceil(len(multikey) / len(title)))
        ncols = len(multikey) if ncols is None else min(len(multikey), ncols)
        nrows = int(np.ceil(len(multikey) / ncols))
        figsize = rcParams['figure.figsize'] if figsize is None else figsize
        ax = []
        for i, gs in enumerate(
                pl.GridSpec(nrows, ncols, pl.figure(None, (figsize[0] * ncols, figsize[1] * nrows), dpi=dpi))):
            if i < len(multikey):
                ax.append(paga(adata, size=size, ax=pl.subplot(gs), scatter_flag=scatter_flag,
                               basis=bases[i] if len(bases) > 1 else basis,
                               color=colors[i] if len(colors) > 1 else color,
                               layer=layers[i] if len(layers) > 1 else layer,
                               vkey=vkeys[i] if len(vkeys) > 1 else vkey,
                               title=title[i] if isinstance(title, (list, tuple)) else title,
                               **kwargs, **paga_kwargs))
        savefig_or_show(dpi=dpi, save=save, show=show)
        if not show: return ax

    else:

        color, layer, vkey, basis = colors[0], layers[0], vkeys[0], basis
        color = default_color(adata) if color is None else color
        size = default_size(adata) / 2 if size is None else size
        groups = groups if isinstance(groups, str) and groups in adata.obs.keys() \
            else 'clusters' if 'clusters' in adata.obs.keys() \
            else 'louvain' if 'louvain' in adata.obs.keys() else None
        _adata = adata[groups_to_bool(adata, groups, groupby=color)] \
            if groups is not None and color in adata.obs.keys() else adata

        if basis in adata.var_names and basis is not None:
            x = adata[:, basis].layers['spliced'] if use_raw else adata[:, basis].layers['Ms']
            y = adata[:, basis].layers['unspliced'] if use_raw else adata[:, basis].layers['Mu']
        elif basis is not None:
            X_emb = adata.obsm['X_' + basis][:, get_components(components, basis)]
            x, y = X_emb[:, 0], X_emb[:, 1]

        if basis is None and pos is None:
            pos = None  # default to paga embedding
        elif pos is None:
            if 'paga' in adata.uns:
                # Recompute the centroid positions
                categories = list(adata.obs[color].cat.categories)
                pos = np.zeros((len(categories), 2))
                for ilabel, label in enumerate(categories):
                    X_emb = adata.obsm['X_' + basis][adata.obs[color] == label, :2]
                    x_pos, y_pos = np.median(X_emb, axis=0)
                    pos[ilabel] = [x_pos, y_pos]
            else:
                raise ValueError(
                    'You need to run `scv.tl.paga` first.')
        paga_kwargs['pos'] = pos

        legend_loc = kwargs.pop('legend_loc', None)
        kwargs['legend_loc'] = 'none' if legend_loc == 'on data' else legend_loc  # let paga handle 'on data'
        if 'frameon' not in paga_kwargs or not paga_kwargs['frameon']:
            paga_kwargs['frameon'] = False
        kwargs['frameon'] = paga_kwargs['frameon']

        ax = pl.figure(None, figsize, dpi=dpi).gca() if ax is None else ax
        if scatter_flag and basis is not None:
            if 'alpha' not in kwargs: kwargs['alpha'] = .5
            ax = scatter(adata, basis=basis, x=x, y=y, vkey=vkey, layer=layer, color=color, size=size, title=title,
                         ax=ax, save=None, zorder=0, show=False, **kwargs)
        else:
            basis = default_basis(adata)
            if basis is not None and init_pos is None or isinstance(init_pos, str):
                cats = adata.obs[groups].cat.categories
                X_emb = adata.obsm['X_' + basis]
                init_pos = np.stack([np.median(X_emb[adata.obs[groups] == c], axis=0) for c in cats])
                paga_kwargs['init_pos'] = init_pos
                kwargs['alpha'] = 0
                x, y = np.ones(len(X_emb)) * np.mean(init_pos[:, 0]), np.ones(len(X_emb)) * np.mean(init_pos[:, 1])
                ax = scatter(adata, x=x, y=y, title=title, ax=ax, save=None, zorder=0, show=False, **kwargs)

        scanpy_paga(adata, ax=ax, show=False,  **paga_kwargs,
                    text_kwds={'zorder': 1000, 'alpha': legend_loc == 'on data'})

        savefig_or_show(dpi=dpi, save=save, show=show)
        if not show: return ax
