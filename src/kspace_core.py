# kspace_core.py

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import LassoSelector
from matplotlib.path import Path
from matplotlib.patches import Polygon

import cv2
from IPython.display import display
import ipywidgets as widgets


class KSpaceInteractive:
    def __init__(self):
        # UI
        self.upload = widgets.FileUpload(accept='image/*', multiple=False)
        self.button = widgets.Button(description="Process Image")
        display(self.upload)
        display(self.button)

        # image and k-space
        self.img = None
        self.k_space = None
        self.masked_kspace = None
        self.mask = None

        # figures
        self.fig = None
        self.ax1 = None
        self.ax2 = None
        self.im_kspace = None
        self.im_recon = None
        self.selector = None
        self.last_lasso_patch = None

        # button events
        self.button.on_click(self.load_and_process_image)

    def load_and_process_image(self, _):
        if not self.upload.value:
            print("no image uploaded")
            return

        content = self.upload.value[0]['content']
        np_arr = np.frombuffer(content, np.uint8)

        img_color = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
        self.img = cv2.resize(img_gray, (256, 256))

        self.k_space = np.fft.fftshift(np.fft.fft2(self.img))
        self.show_k_space()

    def show_k_space(self):
        if self.fig is not None:
            plt.close(self.fig)

        # plot k-space and reconstructed image
        magnitude = np.log(np.abs(self.k_space) + 1)
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(10, 6))
        self.im_kspace = self.ax1.imshow(magnitude, cmap='gray')
        self.ax1.set_title("Select k-space Region")
        self.ax1.axis('off')

        self.ax2.imshow(np.zeros_like(self.img), cmap='gray')
        self.ax2.set_title("Reconstructed Image")
        self.ax2.axis('off')

        # plot lasso mask
        def onselect_lasso(verts):
            self.apply_lasso_mask(verts)
        self.last_lasso_patch = None

        if self.selector is not None:
            self.selector.disconnect_events()
            del self.selector
        self.selector = LassoSelector(self.ax1, onselect_lasso)
        plt.show()

    def apply_lasso_mask(self, verts):
        # get lasso mask from drawn path
        ny, nx = self.k_space.shape
        y, x = np.mgrid[:ny, :nx]
        points = np.vstack((x.flatten(), y.flatten())).T
        path = Path(verts)
        mask_flat = path.contains_points(points)
        self.mask = mask_flat.reshape((ny, nx))
        self.masked_kspace = self.k_space * self.mask

        # clear old
        if self.last_lasso_patch:
            self.last_lasso_patch.remove()

        # display new
        patch = Polygon(verts, closed=True, facecolor='red', edgecolor='black', alpha=0.3)
        self.last_lasso_patch = self.ax1.add_patch(patch)
        self.fig.canvas.draw_idle()
        self.show_reconstructed_image()

    def show_reconstructed_image(self):
        # reconstruct image from masked k-space
        recon = np.fft.ifft2(np.fft.ifftshift(self.masked_kspace))
        recon_abs = np.abs(recon)
        recon_norm = (recon_abs - recon_abs.min()) / (recon_abs.max() - recon_abs.min())

        # plot result
        if self.im_recon is None:
            self.im_recon = self.ax2.imshow(recon_norm, cmap='gray')
        else:
            self.im_recon.set_data(recon_norm)

        self.ax2.set_title("Reconstructed from Masked k-space")
        self.ax2.set_xticks([])
        self.ax2.set_yticks([])
        self.fig.canvas.draw_idle()
