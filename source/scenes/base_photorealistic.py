# -*- coding: utf-8 -*-

############################################################################
#  This file is part of the 4D Light Field Benchmark.                      #
#                                                                          #
#  This work is licensed under the Creative Commons                        #
#  Attribution-NonCommercial-ShareAlike 4.0 International License.         #
#  To view a copy of this license,                                         #
#  visit http://creativecommons.org/licenses/by-nc-sa/4.0/.                #
#                                                                          #
#  Authors: Katrin Honauer & Ole Johannsen                                 #
#  Contact: contact@lightfield-analysis.net                                #
#  Website: www.lightfield-analysis.net                                    #
#                                                                          #
#  The 4D Light Field Benchmark was jointly created by the University of   #
#  Konstanz and the HCI at Heidelberg University. If you use any part of   #
#  the benchmark, please cite our paper "A dataset and evaluation          #
#  methodology for depth estimation on 4D light fields". Thanks!           #
#                                                                          #
#  @inproceedings{honauer2016benchmark,                                    #
#    title={A dataset and evaluation methodology for depth estimation on   #
#           4D light fields},                                              #
#    author={Honauer, Katrin and Johannsen, Ole and Kondermann, Daniel     #
#            and Goldluecke, Bastian},                                     #
#    booktitle={Asian Conference on Computer Vision},                      #
#    year={2016},                                                          #
#    organization={Springer}                                               #
#    }                                                                     #
#                                                                          #
############################################################################


import matplotlib.pyplot as plt
import numpy as np

import settings
from evaluations import radar_chart
from metrics import MSE, BadPix,  BumpinessPlanes, Discontinuities, BumpinessContinSurf, FineFattening, \
    FineThinning, Runtime
from scenes import BaseScene
from utils import plotting, misc
from utils.logger import log


class BasePhotorealistic(BaseScene):

    def __init__(self, img_name, **kwargs):
        super(BasePhotorealistic, self).__init__(img_name, **kwargs)

    @staticmethod
    def get_region_metrics():
        return [BumpinessPlanes(), BumpinessContinSurf(), Discontinuities(), FineFattening(), FineThinning()]

    def get_applicable_metrics_high_res(self):
        return [metric for metric in self.get_region_metrics() if metric.is_applicable_for_high_res_scene(self)]

    def get_applicable_metrics_low_res(self):
        metrics = [metric for metric in self.get_region_metrics() if metric.is_applicable_for_low_res_scene(self)]
        #  add general metrics to low resolution evaluation
        return BaseScene.get_general_metrics() + metrics

    @staticmethod
    def get_applicable_scenes(all_scenes, metric):
        if metric.is_general():
            return all_scenes
        return [s for s in all_scenes if metric.mask_exists(s, settings.LOWRES) or metric.mask_exists(s, settings.HIGHRES)]

    def plot_algo_overview(self, algo_names):
        metrics_low_res = self.get_applicable_metrics_low_res()
        metrics_high_res = self.get_applicable_metrics_high_res()

        # prepare figure
        fontsize = 6
        rows = len(metrics_low_res + metrics_high_res) + 1
        cols = len(algo_names) + 1
        fig = plt.figure(figsize=(cols, rows*1.1))
        grids = plotting.get_grids(fig, rows, cols, axes_pad=-0.2)

        # center view on top left grid cell
        self.set_high_gt_scale()
        plt.sca(grids[0][0])
        plt.imshow(self.get_center_view())
        plt.title("Center View", fontsize=fontsize)
        plt.ylabel("Disparity Map", fontsize=fontsize)

        # mask visualizations + algorithm disparity maps + metric visualizations
        log.info("Computing scores and visualizations for LOW resolution metrics.")
        self.set_low_gt_scale()
        self.plot_metric_rows(grids, algo_names, metrics_low_res, offset=0, fontsize=fontsize)

        log.info("Computing scores and visualizations for HIGH resolution metrics.")
        self.set_high_gt_scale()
        self.plot_metric_rows(grids, algo_names, metrics_high_res, offset=len(metrics_low_res), fontsize=fontsize)

        # finalize figure
        for grid in grids:
            plotting.remove_ticks_from_axes(grid.axes_all)
            plotting.remove_frames_from_axes(grid.axes_all)
        plt.suptitle(self.get_display_name(), fontsize=fontsize+2)

        fig_path = plotting.get_path_to_figure("algo_overview_%s" % self.get_name())
        plotting.save_fig(fig, fig_path, pad_inches=0.1)

    def plot_metric_rows(self, grids, algo_names, metrics, offset, fontsize):
        gt = self.get_gt()
        center_view = self.get_center_view()

        for idx_a, algo_name in enumerate(algo_names):
            log.info("Algorithm: %s" % algo_name)
            algo_result = misc.get_algo_result(self, algo_name)

            # add algorithm disparity map
            plt.sca(grids[0][idx_a + 1])
            cm = plt.imshow(algo_result, **settings.disp_map_args(self))
            plt.title(settings.get_algo_display_name(algo_name), fontsize=fontsize)

            # add colorbar to last disparity map in row
            if idx_a == (len(algo_names) - 1):
                plotting.create_colorbar(cm, cax=grids[0].cbar_axes[0], colorbar_bins=7, fontsize=fontsize)

            # add algorithm metric visualizations
            for idx_m, metric in enumerate(metrics):
                log.info(metric.get_display_name())
                mask = metric.get_evaluation_mask(self)

                plt.sca(grids[idx_m + offset + 1][idx_a + 1])
                cm = self.plot_algo_vis_for_metric(metric, algo_result, gt, mask, self.hidden_gt(), fontsize)

                # add colorbar to last metric visualization in row
                if idx_a == len(algo_names) - 1:
                    plotting.create_colorbar(cm, cax=grids[idx_m + offset + 1].cbar_axes[0],
                                             colorbar_bins=metric.colorbar_bins, fontsize=fontsize)

                # add mask visualizations as 1st column
                if idx_a == 0:
                    plt.sca(grids[idx_m + offset + 1][0])
                    plotting.plot_img_with_transparent_mask(center_view, mask, alpha=0.7, color=settings.color_mask)
                    plt.ylabel(metric.get_short_name(), fontsize=fontsize)
                    plt.title("Region Mask", fontsize=fontsize)

    def plot_algo_vis_for_metric(self, metric, algo_result, gt, mask, hide_gt=False, fontsize=10):
        score, vis = metric.get_score(algo_result, gt, self, with_visualization=True)

        if hide_gt and metric.pixelize_results():
            vis = misc.pixelize(vis)

        # plot algorithm disparity map as background
        plt.imshow(algo_result, **settings.disp_map_args(self, cmap="gray"))

        # plot masked metric visualization on top
        cm = plt.imshow(np.ma.masked_array(vis, mask=~mask), **settings.metric_args(metric))
        plt.title(metric.format_score(score), fontsize=fontsize)

        return cm

    @staticmethod
    def get_all_scores(algo_names, metrics, scenes):
        scores_algos_metric = np.full((len(algo_names), len(metrics)), fill_value=np.nan)

        for idx_m, metric in enumerate(metrics):
            log.info("Computing scores for: %s" % metric.get_display_name().replace("\n", ""))
            if metric.evaluate_on_high_res():
                gt_scale = 10.0
            else:
                gt_scale = 1.0

            applicable_scenes = BasePhotorealistic.get_applicable_scenes(scenes, metric)
            for scene in applicable_scenes:
                scene.gt_scale = gt_scale

            scores_algos_metric[:, idx_m] = BasePhotorealistic.get_average_scores(algo_names, metric, applicable_scenes)

        return scores_algos_metric

    @staticmethod
    def plot_radar_chart(algo_names, scenes, fig_path, max_per_metric=None):
        metrics = [MSE(),
                   BadPix(),
                   BumpinessPlanes(descr="Planar\nSurfaces"),
                   BumpinessContinSurf(descr="Continuous\nSurfaces"),
                   FineThinning(descr="Fine Structure\nThinning"),
                   FineFattening(descr="Fine Structure\nFattening"),
                   Discontinuities(descr="Discontinuity\nRegions"),
                   Runtime(log=True)]

        metric_names = [m.get_display_name() for m in metrics]
        scores_algos_metric = BasePhotorealistic.get_all_scores(algo_names, metrics, scenes)

        if max_per_metric is None:
            max_per_metric = [20, 60, 5, 5, 16, 100, 80, 6]

        radar_chart.plot(scores_algos_metric, metric_names, algo_names, fig_path, max_per_metric)