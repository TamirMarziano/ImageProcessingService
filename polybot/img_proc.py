from pathlib import Path
from matplotlib.image import imread, imsave


def rgb2gray(rgb):
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    gray = 0.2989 * r + 0.5870 * g + 0.1140 * b
    return gray


class Img:

    def __init__(self, path):
        """
        Do not change the constructor implementation
        """
        self.path = Path(path)
        self.data = rgb2gray(imread(path)).tolist()

    def save_img(self):
        """
        Do not change the below implementation
        """
        new_path = self.path.with_name(self.path.stem + '_filtered' + self.path.suffix)
        imsave(new_path, self.data, cmap='gray')
        return new_path

    def blur(self, blur_level=16):

        height = len(self.data)
        width = len(self.data[0])
        filter_sum = blur_level ** 2

        result = []
        for i in range(height - blur_level + 1):
            row_result = []
            for j in range(width - blur_level + 1):
                sub_matrix = [row[j:j + blur_level] for row in self.data[i:i + blur_level]]
                average = sum(sum(sub_row) for sub_row in sub_matrix) // filter_sum
                row_result.append(average)
            result.append(row_result)

        self.data = result

    def contour(self):
        for i, row in enumerate(self.data):
            res = []
            for j in range(1, len(row)):
                res.append(abs(row[j-1] - row[j]))

            self.data[i] = res

    def rotate(self):
        mat = self.data
        len1 = len(mat) - 1
        len2 = len(mat[0])
        tmp_lst = []
        finel_lst = []
        for i in range(len2):
            for j in range(len1, -1, -1):
                tmp_lst.append(mat[j][i])
            finel_lst.append(tmp_lst)
            tmp_lst = []
        self.data = finel_lst

    def salt_n_pepper(self):
        # TODO remove the `raise` below, and write your implementation
        raise NotImplementedError()

    def concat(self, other_img, direction='horizontal'):
        mat = self.data
        mat2 = other_img.data
        if len(mat) == len(mat2) and len(mat[0]) == len(mat2[0]):
            fin_lst = []
            tmp_lst = []
            for i in range(len(mat)):
                for j in range(len(mat[0])):
                    tmp_lst.append(mat[i][j])
                for k in range(len(mat[0])):
                    tmp_lst.append(mat2[i][k])
                fin_lst.append(tmp_lst)
                tmp_lst = []
            self.data = fin_lst
    def segment(self):
        # TODO remove the `raise` below, and write your implementation
        raise NotImplementedError()


if __name__ == '__main__':
    my_img = Img('/home/tamir/Desktop/YuvalTamir.jpg')
    my_img2 = Img('/home/tamir/Desktop/YuvalTamir.jpg')
    my_img.concat(my_img2, direction='horizontal')
    my_img.save_img()
