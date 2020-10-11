import time

import numpy as np
import tensorflow as tf

import awesome_gans.image_utils as iu
import awesome_gans.lsgan.lsgan_model as lsgan
from awesome_gans.datasets import CiFarDataSet as DataSet
from awesome_gans.datasets import DataIterator

results = {'output': './gen_img/', 'model': './model/LSGAN-model.ckpt'}

train_step = {
    'epoch': 201,
    'batch_size': 64,
    'global_step': 200001,
    'logging_interval': 1000,
}


def main():
    start_time = time.time()  # Clocking start

    # Training, Test data set
    # loading Cifar DataSet
    ds = DataSet(height=32, width=32, channel=3, ds_path='D:\\DataSet/cifar/cifar-10-batches-py/', ds_name='cifar-10')

    # saving sample images
    test_images = np.reshape(iu.transform(ds.test_images[:16], inv_type='127'), (16, 32, 32, 3))
    iu.save_images(test_images, size=[4, 4], image_path=results['output'] + 'sample.png', inv_type='127')

    ds_iter = DataIterator(x=ds.train_images, y=None, batch_size=train_step['batch_size'], label_off=True)

    # GPU configure
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    with tf.Session(config=config) as s:
        # GAN Model
        model = lsgan.LSGAN(s, train_step['batch_size'])

        # Initializing variables
        s.run(tf.global_variables_initializer())

        # Load model & Graph & Weights
        saved_global_step = 0

        ckpt = tf.train.get_checkpoint_state('./model/')
        if ckpt and ckpt.model_checkpoint_path:
            # Restores from checkpoint
            model.saver.restore(s, ckpt.model_checkpoint_path)

            saved_global_step = int(ckpt.model_checkpoint_path.split('/')[-1].split('-')[-1])
            print("[+] global step : %d" % saved_global_step, " successfully loaded")
        else:
            print('[-] No checkpoint file found')

        global_step = saved_global_step
        start_epoch = global_step // (len(ds.train_images) // model.batch_size)
        ds_iter.pointer = saved_global_step % (len(ds.train_images) // model.batch_size)  # recover n_iter
        for epoch in range(start_epoch, train_step['epoch']):
            for batch_x in ds_iter.iterate():
                batch_x = iu.transform(batch_x, inv_type='127')
                batch_x = np.reshape(batch_x, [-1] + model.image_shape[1:])
                batch_z = np.random.uniform(-1.0, 1.0, [model.batch_size, model.z_dim]).astype(np.float32)

                # Update D network
                _, d_loss = s.run([model.d_op, model.d_loss], feed_dict={model.x: batch_x, model.z: batch_z})

                # Update G network
                _, g_loss = s.run([model.g_op, model.g_loss], feed_dict={model.x: batch_x, model.z: batch_z})

                # Logging
                if global_step % train_step['logging_interval'] == 0:
                    d_loss, g_loss, summary = s.run(
                        [model.d_loss, model.g_loss, model.merged], feed_dict={model.x: batch_x, model.z: batch_z}
                    )

                    # Print loss
                    print(
                        "[+] Epoch %02d Step %08d => " % (epoch, global_step),
                        " D loss : {:.8f}".format(d_loss),
                        " G loss : {:.8f}".format(g_loss),
                    )

                    # Training G model with sample image and noise
                    sample_z = np.random.uniform(-1.0, 1.0, [model.sample_num, model.z_dim]).astype(np.float32)
                    samples = s.run(
                        model.g,
                        feed_dict={
                            model.z: sample_z,
                        },
                    )

                    # Summary saver
                    model.writer.add_summary(summary, global_step)

                    # Export image generated by model G
                    sample_image_height = model.sample_size
                    sample_image_width = model.sample_size
                    sample_dir = results['output'] + 'train_{:08d}.png'.format(global_step)

                    # Generated image save
                    iu.save_images(
                        samples, size=[sample_image_height, sample_image_width], image_path=sample_dir, inv_type='127'
                    )

                    # Model save
                    model.saver.save(s, results['model'], global_step)

                global_step += 1

    end_time = time.time() - start_time  # Clocking end

    # Elapsed time
    print("[+] Elapsed time {:.8f}s".format(end_time))

    # Close tf.Session
    s.close()


if __name__ == '__main__':
    main()
