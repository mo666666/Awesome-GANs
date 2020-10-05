import sys
import time

import tensorflow as tf

import awesome_gans.discogan.discogan_model as discogan
import awesome_gans.image_utils as iu
from awesome_gans.datasets import Pix2PixDataSet as DataSets

# import numpy as np


sys.path.insert(0, '../')

results = {
    'sample_output': './gen_img/',
    'model': './model/DiscoGAN-model.ckpt'
}
paras = {
    'epoch': 200,
    'batch_size': 64,
    'logging_interval': 5
}


def main():
    start_time = time.time()  # clocking start

    # Dataset
    dataset = DataSets(height=64,
                       width=64,
                       channel=3,
                       ds_path='D:/DataSets/pix2pix/',
                       ds_name="vangogh2photo")

    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    with tf.Session(config=config) as s:
        # DiscoGAN model
        model = discogan.DiscoGAN(s)

        # load model & graph & weight
        global_step = 0
        ckpt = tf.train.get_checkpoint_state('./model/')
        if ckpt and ckpt.model_checkpoint_path:
            # Restores from checkpoint
            model.saver.restore(s, ckpt.model_checkpoint_path)

            global_step = ckpt.model_checkpoint_path.split('/')[-1].split('-')[-1]
            print("[+] global step : %s" % global_step, " successfully loaded")
        else:
            print('[-] No checkpoint file found')

        # initializing variables
        tf.global_variables_initializer().run()

        d_overpowered = False  # G loss > D loss * 2
        for epoch in range(paras['epoch']):
            for step in range(1000):
                offset_a = (step * paras['batch_size']) % (dataset.images_a.shape[0] - paras['batch_size'])
                offset_b = (step * paras['batch_size']) % (dataset.images_b.shape[0] - paras['batch_size'])

                # batch data set
                batch_a = dataset.images_a[offset_a:(offset_a + paras['batch_size']), :]
                batch_b = dataset.images_b[offset_b:(offset_b + paras['batch_size']), :]

                # update D network
                if not d_overpowered:
                    s.run(model.d_op, feed_dict={model.A: batch_a})

                # update G network
                s.run(model.g_op, feed_dict={model.B: batch_b})

                if epoch % paras['logging_interval'] == 0:
                    d_loss, g_loss, summary = s.run([
                        model.d_loss,
                        model.g_loss,
                        model.merged
                    ], feed_dict={
                        model.A: batch_a,
                        model.B: batch_b
                    })

                    # print loss
                    print("[+] Epoch %03d Step %04d => " % (epoch, global_step),
                          " D loss : {:.8f}".format(d_loss),
                          " G loss : {:.8f}".format(g_loss))

                    # update overpowered
                    d_overpowered = d_loss < g_loss / 2.

                    # training G model with sample image and noise
                    ab_samples = s.run(model.G_s2b, feed_dict={model.A: batch_a})
                    ba_samples = s.run(model.G_b2s, feed_dict={model.B: batch_b})

                    # summary saver
                    model.writer.add_summary(summary, global_step=global_step)

                    # export image generated by model G
                    sample_image_height = model.sample_size
                    sample_image_width = model.sample_size
                    sample_ab_dir = results['sample_output'] + 'train_A_{0}_{1}.png'.format(epoch, global_step)
                    sample_ba_dir = results['sample_output'] + 'train_B_{0}_{1}.png'.format(epoch, global_step)

                    # Generated image save
                    iu.save_images(ab_samples, size=[sample_image_height, sample_image_width],
                                   image_path=sample_ab_dir)
                    iu.save_images(ba_samples, size=[sample_image_height, sample_image_width],
                                   image_path=sample_ba_dir)

                    # model save
                    model.saver.save(s, results['model'], global_step=global_step)

        end_time = time.time() - start_time

        # elapsed time
        print("[+] Elapsed time {:.8f}s".format(end_time))

        # close tf.Session
        s.close()


if __name__ == '__main__':
    main()
